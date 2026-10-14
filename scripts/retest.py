#!/usr/bin/env python3
"""Robustness (PROTOCOL.md amendment 2): test-retest. Re-ask every panel model about 500 random census passages
(seed 99, passages that already have all three labels) and report how often each model, and the panel, gives the
same label as in the census run. Output: retest.json, retest_labels.jsonl
usage: SANECITE_DATA=... retest.py [n]"""
import collections, json, os, random, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__)); import panel as P, classify as C
DATA = os.environ["SANECITE_DATA"]; TOKEN = os.environ.get("CF_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
recs = {}
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: r = json.loads(l)
    except Exception: continue
    if r["status"] == "ok" and not r.get("is_notice"): recs[r["pair_id"]] = r
L = collections.defaultdict(dict)
for tag in ("jev", "clef", "gemma"):
    for l in open(f"{DATA}/stage3_{tag}.jsonl"):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("label") and r["pair_id"] in recs: L[(r["pair_id"], r["ctx"])][r["model"]] = r
pool = sorted(k for k, d in L.items() if all(m in d for m in P.PANEL))
draw = random.Random(99).sample(pool, N)

def ask(model, pid, i):
    rec = recs[pid]
    for _ in range(3):
        try:
            x = C.jev(rec, model=model, i=i) if model in ("typesafe/jev", "@cf/cloudflare/clef") else C.chat(model, rec, TOKEN, i=i)
        except Exception as e:
            x = {"error": str(e)[:120]}
        if x.get("label"): return x
    return x

out_rows, same = [], collections.Counter()
with cf.ThreadPoolExecutor(12) as ex:
    futs = {ex.submit(ask, m, pid, i): (m, pid, i) for pid, i in draw for m in P.PANEL}
    new = collections.defaultdict(dict)
    for fu in cf.as_completed(futs):
        m, pid, i = futs[fu]; x = fu.result(); new[(pid, i)][m] = x
        out_rows.append({"pair_id": pid, "ctx": i, "model": m, "label": x.get("label"), "stance": x.get("stance"),
                         "use": x.get("use"), "error": x.get("error")})
res = {"n_passages": N, "seed": 99, "per_model": {}, "panel": None}
for m in P.PANEL:
    pairs = [(L[k][m]["label"], new[k][m].get("label")) for k in draw if new[k][m].get("label")]
    res["per_model"][m] = {"n": len(pairs), "same_label": round(sum(a == b for a, b in pairs) / max(1, len(pairs)), 4)}
pp = []
for pid, i in draw:
    if all(new[(pid, i)][m].get("label") for m in P.PANEL):
        t = " ".join(C.passage(recs[pid], i))
        pp.append((P.combine(L[(pid, i)], t)[0], P.combine(new[(pid, i)], t)[0]))
res["panel"] = {"n": len(pp), "same_label": round(sum(a == b for a, b in pp) / max(1, len(pp)), 4)}
with open(f"{DATA}/retest_labels.jsonl", "w") as f:
    for r in out_rows: f.write(json.dumps(r) + "\n")
json.dump(res, open(f"{DATA}/retest.json", "w"), indent=1)
print(json.dumps(res, indent=1))
