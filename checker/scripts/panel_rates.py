#!/usr/bin/env python3
"""Rates for one batch with the chosen panel (METHOD_CHOSEN_v2_2026-10-22.md): twostep vote of 5 voters.
Optionally scores the panel against a gold reference.
Usage: panel_rates.py BATCH_DIR [GOLD.jsonl]"""
import collections, glob, json, math, os, sys

VOTERS = [("v2", "deepseek-v4.1-flash-1017"), ("v2", "kimi-k2.6"), ("v3", "gpt-oss-120b"),
          ("v3", "llama-3.3-70b-instruct-fp8-fast"), ("v3", "qwen3.8-27b")]  # METHOD_CHOSEN_v2_2026-10-22.md


def twostep(vs):
    judged = [v for v in vs if v != "cannot_tell"]
    if not judged: return "cannot_tell"
    errs = [v for v in judged if v in ("minor", "major")]
    if len(errs) * 2 > len(judged): return "major" if sum(v == "major" for v in errs) * 2 >= len(errs) else "minor"
    if len(errs) * 2 == len(judged): return "cannot_tell"
    return "accurate"


def wilson(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def kappa(a, b, cats):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def main():
    b = sys.argv[1]
    votes = collections.defaultdict(dict)
    types = collections.defaultdict(dict)
    for prompt, model in VOTERS:
        f = os.path.join(b, prompt, model.replace(".", "_").replace("-", "_") + ".jsonl")
        for l in open(f):
            j = json.loads(l)
            if j.get("parsed"):
                votes[j["draw"]][(prompt, model)] = j["parsed"]["verdict"]
                types[j["draw"]][(prompt, model)] = j["parsed"]["citation_type"]
    full = {d: v for d, v in votes.items() if len(v) == len(VOTERS)}
    panel, ptype = {}, {}
    for d, v in full.items():
        panel[d] = twostep(list(v.values()))
        t = collections.Counter(types[d].values()).most_common(1)[0]
        ptype[d] = t[0] if t[1] > len(VOTERS) / 2 else "split"
    judged = [d for d in panel if panel[d] != "cannot_tell"]
    maj = sum(panel[d] == "major" for d in judged); err = sum(panel[d] in ("minor", "major") for d in judged)
    out = {"pairs_all_voters": len(full), "panel_verdicts": dict(collections.Counter(panel.values())),
           "major": {"k": maj, "n": len(judged), "pct": round(100 * maj / len(judged), 1) if judged else None, "ci95": wilson(maj, len(judged))},
           "any_error": {"k": err, "n": len(judged), "pct": round(100 * err / len(judged), 1) if judged else None, "ci95": wilson(err, len(judged))}}
    by = {}
    for t in ("specific_claim", "background", "method_or_tool", "data_source"):
        ds = [d for d in judged if ptype[d] == t]
        k = sum(panel[d] == "major" for d in ds)
        by[t] = {"n": len(ds), "major_pct": round(100 * k / len(ds), 1) if ds else None, "ci95": wilson(k, len(ds))}
    out["major_by_type"] = by
    if len(sys.argv) > 2:
        gold = {json.loads(l)["draw"]: json.loads(l)["verdict"] for l in open(sys.argv[2])}
        ds = [d for d in gold if d in panel]
        g = [gold[d] for d in ds]; p = [panel[d] for d in ds]
        jj = [i for i, x in enumerate(g) if x != "cannot_tell"]
        gb = ["e" if g[i] in ("minor", "major") else "o" for i in jj]; pb = ["e" if p[i] in ("minor", "major") else "o" for i in jj]
        gm = ["m" if g[i] == "major" else "n" for i in jj]; pm = ["m" if p[i] == "major" else "n" for i in jj]
        tp = sum(x == y == "m" for x, y in zip(gm, pm))
        out["vs_gold"] = {"n": len(ds), "kappa_error": kappa(gb, pb, ("e", "o")), "kappa_major": kappa(gm, pm, ("m", "n")),
                          "major_recall": round(tp / gm.count("m"), 3) if gm.count("m") else None,
                          "major_precision": round(tp / pm.count("m"), 3) if pm.count("m") else None,
                          "gold_major_pct": round(100 * gm.count("m") / len(jj), 1) if jj else None,
                          "gold_error_pct": round(100 * gb.count("e") / len(jj), 1) if jj else None}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
