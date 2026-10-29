#!/usr/bin/env python3
"""Compare the blind Claude read of 100 pairs with the panel and with each model. Usage: compare_blind.py OUT.json"""
import collections, glob, json, os, sys

D = os.path.expanduser("work/checker")
V = ("accurate", "minor", "major", "cannot_tell")
blind = {}
for f in sorted(glob.glob(f"{D}/blind/claude-*.jsonl")):
    for l in open(f):
        j = json.loads(l); blind[j["draw"]] = j
votes = collections.defaultdict(dict)
for f in glob.glob(f"{D}/data/judged/*.jsonl"):
    for l in open(f):
        j = json.loads(l)
        if j.get("parsed"): votes[j["draw"]][j["model"]] = j["parsed"]["verdict"]


def majority(vals):
    c = collections.Counter(vals).most_common(1)
    return c[0][0] if c and c[0][1] >= 2 else "split"


def kappa(a, b):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in V)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


draws = [d for d in blind if len(votes.get(d, {})) == 3]
out = {"n": len(draws), "blind_verdicts": dict(collections.Counter(blind[d]["verdict"] for d in draws))}
panel = {d: majority(list(votes[d].values())) for d in draws}
out["panel_verdicts"] = dict(collections.Counter(panel.values()))
b = [blind[d]["verdict"] for d in draws]
p = [panel[d] for d in draws]
out["panel_vs_blind_agreement"] = round(sum(x == y for x, y in zip(b, p)) / len(draws), 3) if draws else None
out["panel_vs_blind_kappa"] = kappa(b, [x if x in V else "cannot_tell" for x in p])
# collapsed: error (minor or major) vs accurate, on pairs both judged
both = [d for d in draws if blind[d]["verdict"] != "cannot_tell" and panel[d] in ("accurate", "minor", "major")]
bb = ["error" if blind[d]["verdict"] in ("minor", "major") else "ok" for d in both]
pp = ["error" if panel[d] in ("minor", "major") else "ok" for d in both]
out["error_vs_ok"] = {"n": len(both), "agree": round(sum(x == y for x, y in zip(bb, pp)) / len(both), 3) if both else None,
                      "blind_error_rate": round(bb.count("error") / len(both), 3) if both else None,
                      "panel_error_rate": round(pp.count("error") / len(both), 3) if both else None,
                      "blind_major_rate": round(sum(blind[d]["verdict"] == "major" for d in both) / len(both), 3) if both else None,
                      "panel_major_rate": round(sum(panel[d] == "major" for d in both) / len(both), 3) if both else None}
out["confusion_blind_rows_panel_cols"] = {bv: dict(collections.Counter(panel[d] for d in draws if blind[d]["verdict"] == bv)) for bv in V}
out["per_model_vs_blind"] = {}
for m in sorted({m for d in draws for m in votes[d]}):
    mv = [votes[d][m] for d in draws]
    out["per_model_vs_blind"][m.split("/")[-1]] = {"agreement": round(sum(x == y for x, y in zip(b, mv)) / len(draws), 3),
                                                   "kappa": kappa(b, mv),
                                                   "major_calls": mv.count("major")}
json.dump(out, open(sys.argv[1], "w") if len(sys.argv) > 1 else sys.stdout, indent=1)
print(json.dumps(out, indent=1))
