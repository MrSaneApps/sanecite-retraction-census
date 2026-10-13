#!/usr/bin/env python3
"""Pair-level accuracy of v3.1 panel variants against Claude's labels, plus accuracy by route.
usage: eval_panel.py <records.jsonl> <labels.jsonl> <gold.json>"""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(__file__)); import panel as P, classify as C
recs = {json.loads(l)["pair_id"]: json.loads(l) for l in open(sys.argv[1])}
L = collections.defaultdict(dict)
for l in open(sys.argv[2]):
    try: r = json.loads(l)
    except Exception: continue
    if r.get("label"): L[(r["pair_id"], r.get("ctx", 0))][r["model"]] = r
G = json.load(open(sys.argv[3]))["items"]
RANK = {"aware": 3, "substantive": 2, "perfunctory": 1, "unclear": 0}
def pair(g, fn):
    out, routes = [], []
    for i in range(len(g["ctx"])):
        rows = L.get((g["pair_id"], i), {})
        lab, route = fn(rows, " ".join(C.passage(recs[g["pair_id"]], i)))
        if lab is None: return None, None
        out.append(lab); routes.append(route)
    worst = "split" if "split" in routes else "majority" if "majority" in routes else "unanimous"
    return max(out, key=lambda x: RANK[x]), worst
variants = {
  "jev alone": lambda rows, t: ((rows.get(P.JEV) or {}).get("label"), "unanimous"),
  "gemma alone": lambda rows, t: ((rows.get(P.GEMMA) or {}).get("label"), "unanimous"),
  "clef alone": lambda rows, t: ((rows.get(P.CLEF) or {}).get("label"), "unanimous"),
  "PANEL v3.1": P.combine,
}
for name, fn in variants.items():
    ok = n = 0; by = collections.Counter(); byok = collections.Counter(); errs = []
    for g in G:
        lab, route = pair(g, fn)
        if lab is None: continue
        n += 1; hit = lab == g["pair"]; ok += hit; by[route] += 1; byok[route] += hit
        if not hit: errs.append(f"#{g['i']} gold={g['pair']} got={lab} ({route})")
    print(f"{name:12s} {ok}/{n} = {ok/max(n,1):.1%}  " + "  ".join(f"{k}: {byok[k]}/{by[k]}" for k in ("unanimous", "majority", "split") if by[k]))
    if name == "PANEL v3.1" and "--show" in sys.argv: print("   " + "\n   ".join(errs))
# two-model panel (gemma + clef, clef breaks ties): what census contexts without a jev vote get
two = lambda rows, t: P.combine({m: r for m, r in rows.items() if m != P.JEV}, t)
for name, fn in {"PANEL 2-model": two}.items():
    ok = n = 0; by = collections.Counter(); byok = collections.Counter()
    for g in G:
        lab, route = pair(g, fn)
        if lab is None: continue
        n += 1; hit = lab == g["pair"]; ok += hit; by[route] += 1; byok[route] += hit
    print(f"{name:12s} {ok}/{n} = {ok/max(n,1):.1%}  " + "  ".join(f"{k}: {byok[k]}/{by[k]}" for k in ("unanimous", "majority", "split") if by[k]))
