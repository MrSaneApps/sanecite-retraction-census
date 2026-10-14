#!/usr/bin/env python3
"""Blind holdout for the frozen v3.1 pipeline: a simple random sample of census pairs
(seed 31337), never used in development, extracted with the frozen extractor.
usage: SANECITE_DATA=... holdout_v31.py draw [N]   -> $DATA/holdout_v31.jsonl + holdout_v31_view.txt (no labels)
       SANECITE_DATA=... holdout_v31.py score       -> compares $DATA/holdout_v31_labels.jsonl (models) with
                                                       $DATA/holdout_v31_gold.json (Claude, blind) -> holdout_v31_score.json"""
import json, os, random, sys, math, collections
sys.path.insert(0, os.path.dirname(__file__)); import extract as E, panel as P, classify as C
DATA = os.environ["SANECITE_DATA"]; PILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANK = {"aware": 3, "substantive": 2, "perfunctory": 1, "unclear": 0}
def wilson(k, n, z=1.96):
    if not n: return [0, 0]
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - h) / d, 4), round((c + h) / d, 4)]
def draw(N, seed=31337, tag="holdout_v31"):
    used = set()
    for f in [f"{DATA}/holdout_v31.jsonl"] if tag != "holdout_v31" else []:
        for l in open(f): used.add(json.loads(l)["pair_id"])
    for f in ("calib_v3.jsonl", "oldgold_v3.jsonl", "stage2_sample.jsonl", "devpool.jsonl"):
        for l in open(f"{PILOT}/data/{f}"):
            try: used.add(json.loads(l)["pair_id"])
            except Exception: pass
    papers = [json.loads(l) for l in open(f"{DATA}/stage1_papers.jsonl")]
    pool = sorted(((p, c) for p in papers for c in p["oa_citers"] if f"{p['pmid']}>{c['pmcid']}" not in used), key=lambda pc: (int(pc[0]["pmid"]), pc[1]["pmcid"]))
    random.Random(seed).shuffle(pool)
    out = []
    for p, c in pool:
        d = p.get("original_date", ""); y = int(d.split("/")[-1]) if d.count("/") == 2 and d.split("/")[-1].isdigit() else None
        x = E.fetch_xml(c["pmcid"])
        r = E.contexts(x, p["pmid"], p["doi"], p["title"], year=y) if x else {"status": "no-fulltext"}
        if r.get("status") != "ok" or r.get("is_notice"): continue
        out.append({"pair_id": f"{p['pmid']}>{c['pmcid']}", "retracted_pmid": p["pmid"], "retracted_title": p["title"], "reason": p["reason"],
                    "retraction_year": p["retraction_year"], "citing_pmcid": c["pmcid"], "citing_year": c["year"], **r})
        if len(out) >= N: break
    with open(f"{DATA}/{tag}.jsonl", "w") as f:
        for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{DATA}/{tag}_view.txt", "w") as f:
        for i, r in enumerate(out):
            f.write(f"#{i} T: {r['retracted_title'][:110]}\n")
            for j, c in enumerate(r["contexts"]):
                f.write(f"  [{j}] ({c.get('where','text')}; {c['section'][:30]}) {c['before'][-200:]} <<{c['sentence']}>> {c['after'][:140]}\n")
    print("holdout", len(out))
def score():
    recs = {json.loads(l)["pair_id"]: json.loads(l) for l in open(f"{DATA}/holdout_v31.jsonl")}
    G = json.load(open(f"{DATA}/holdout_v31_gold.json"))["items"]
    L = collections.defaultdict(dict)
    for l in open(f"{DATA}/holdout_v31_labels.jsonl"):
        r = json.loads(l)
        if r.get("label"): L[(r["pair_id"], r["ctx"])][r["model"]] = r
    res = collections.Counter(); conf = collections.Counter(); ctx_ok = ctx_n = 0; byroute = collections.Counter(); byroute_ok = collections.Counter()
    for g in G:
        rec = recs[g["pair_id"]]; labs, routes = [], []
        for i in range(len(g["ctx"])):
            lab, route = P.combine(L[(g["pair_id"], i)], " ".join(C.passage(rec, i)))
            labs.append(lab); routes.append(route); ctx_n += 1; ctx_ok += lab == g["ctx"][i]
            byroute[route] += 1; byroute_ok[route] += lab == g["ctx"][i]
        pl = max(labs, key=lambda x: RANK[x]); res["n"] += 1; res["ok"] += pl == g["pair"]; conf[(g["pair"], pl)] += 1
        res["s_gold"] += g["pair"] == "substantive"; res["s_panel"] += pl == "substantive"
    out = {"pairs": res["n"], "pair_agree": res["ok"], "pair_accuracy": round(res["ok"] / res["n"], 4), "pair_wilson95": wilson(res["ok"], res["n"]),
           "contexts": ctx_n, "context_accuracy": round(ctx_ok / ctx_n, 4), "context_wilson95": wilson(ctx_ok, ctx_n),
           "by_route": {k: {"n": byroute[k], "agree": byroute_ok[k], "accuracy": round(byroute_ok[k] / byroute[k], 4), "wilson95": wilson(byroute_ok[k], byroute[k])} for k in byroute},
           "substantive_rate_gold": round(res["s_gold"] / res["n"], 4), "substantive_rate_panel": round(res["s_panel"] / res["n"], 4),
           "confusion_gold_to_panel": {f"{a}->{b}": v for (a, b), v in sorted(conf.items())}}
    json.dump(out, open(f"{DATA}/holdout_v31_score.json", "w"), indent=1); print(json.dumps(out, indent=1))
if __name__ == "__main__":
    if sys.argv[1] == "draw": draw(int(sys.argv[2]) if len(sys.argv) > 2 else 300)
    elif sys.argv[1] == "confirm": draw(int(sys.argv[2]) if len(sys.argv) > 2 else 150, seed=4242, tag="confirm_v33")  # fresh blind set for the frozen v3.3
    else: score()
