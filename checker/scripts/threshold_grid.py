#!/usr/bin/env python3
"""Vote-count rules for the chosen 5 voters, scored on several gold sets. Rule (e, m): a citation is an error when at
least e voters say minor or major; it is major when at least m voters say major. Fewer than e error votes and fewer
than e accurate votes = cannot_tell. Usage: threshold_grid.py BATCH_DIR... (each with gold/gold.jsonl)"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from panel_rates import VOTERS, kappa


def load(b):
    votes = collections.defaultdict(dict)
    for prompt, model in VOTERS:
        for l in open(os.path.join(b, prompt, model.replace(".", "_").replace("-", "_") + ".jsonl")):
            j = json.loads(l)
            if j.get("parsed"): votes[j["draw"]][(prompt, model)] = j["parsed"]["verdict"]
    gold = {json.loads(l)["draw"]: json.loads(l)["verdict"] for l in open(os.path.join(b, "gold", "gold.jsonl"))}
    return {d: v for d, v in votes.items() if len(v) == len(VOTERS)}, gold


def rule(vs, e, m):
    ne = sum(v in ("minor", "major") for v in vs); na = sum(v == "accurate" for v in vs); nm = sum(v == "major" for v in vs)
    if ne >= e: return "major" if nm >= m else "minor"
    if na >= len(vs) - e + 1: return "accurate"
    return "cannot_tell"


def score(votes, gold, e, m):
    ds = [d for d in gold if d in votes and gold[d] != "cannot_tell"]
    g = [gold[d] for d in ds]; p = [rule(list(votes[d].values()), e, m) for d in ds]
    gb = ["e" if x in ("minor", "major") else "o" for x in g]; pb = ["e" if x in ("minor", "major") else "o" for x in p]
    gm = ["m" if x == "major" else "n" for x in g]; pm = ["m" if x == "major" else "n" for x in p]
    return kappa(gb, pb, ("e", "o")), kappa(gm, pm, ("m", "n")), sum(x == "cannot_tell" for x in p), sum(x == "m" for x in pm), gm.count("m")


def main():
    sets = {os.path.basename(b.rstrip("/")): load(b) for b in sys.argv[1:]}
    rows = []
    for e in range(1, 6):
        for m in range(1, 6):
            r = {k: score(v[0], v[1], e, m) for k, v in sets.items()}
            worst = min(x[0] + x[1] for x in r.values())
            rows.append((worst, e, m, r))
    rows.sort(key=lambda x: -x[0])
    for worst, e, m, r in rows[:10]:
        print("e>=%d m>=%d worst=%.3f  " % (e, m, worst) + "  ".join("%s kE=%.3f kM=%.3f ct=%d pm=%d/gm=%d" % ((k,) + v) for k, v in r.items()))


if __name__ == "__main__":
    main()
