#!/usr/bin/env python3
"""Stage 3 pilot analysis, exactly as PROTOCOL.md fixes it. Usage: analyze.py SAMPLE.jsonl JUDGED_DIR [OUT.json]"""
import collections, glob, json, math, os, re, sys

VERDICTS = ("accurate", "minor", "major", "cannot_tell")


def wilson(k, n, z=1.96):
    if not n: return (None, None)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def pct(k, n):
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None,
            "ci95": [round(100 * lo, 1), round(100 * hi, 1)] if n else None}


def majority(vals):
    c = collections.Counter(v for v in vals if v)
    if not c: return None
    v, k = c.most_common(1)[0]
    return v if k >= 2 else "split"


def fleiss(table):
    """table: list of per-item category counts (each row sums to the same number of raters)."""
    rows = [r for r in table if sum(r) >= 2]
    if not rows: return None
    m = sum(rows[0]); rows = [r for r in rows if sum(r) == m]
    N, k = len(rows), len(rows[0])
    p = [sum(r[j] for r in rows) / (N * m) for j in range(k)]
    P = [(sum(x * x for x in r) - m) / (m * (m - 1)) for r in rows]
    Pbar, Pe = sum(P) / N, sum(x * x for x in p)
    return round((Pbar - Pe) / (1 - Pe), 3) if Pe < 1 else None


def main():
    sample, jdir = sys.argv[1], sys.argv[2]
    rows = {}
    for l in open(sample):
        try: r = json.loads(l)
        except json.JSONDecodeError: continue
        if r["status"] == "ok": rows[r["draw"]] = r
    status = collections.Counter()
    for l in open(sample):
        try: status[json.loads(l)["status"]] += 1
        except json.JSONDecodeError: pass
    votes = collections.defaultdict(dict)
    usage = collections.defaultdict(lambda: {"calls": 0, "neurons": 0.0, "pt": 0, "ct": 0, "lenient": 0, "quote_found": 0, "quotes": 0})
    for f in glob.glob(os.path.join(jdir, "*.jsonl")):
        for l in open(f):
            j = json.loads(l)
            if not j.get("parsed") or j["draw"] not in rows: continue
            votes[j["draw"]][j["model"]] = j["parsed"]  # last parsed answer per (pair, model)
            u = usage[j["model"]]; u["calls"] += 1
            for k in ("neurons", "pt", "ct"): u[k] += (j.get("usage") or {}).get(k, 0) or 0
            u["lenient"] += bool(j["parsed"].get("lenient_parse"))
            if j.get("quote_found") is not None: u["quotes"] += 1; u["quote_found"] += bool(j["quote_found"])
    models = sorted({m for v in votes.values() for m in v})
    full = {d: v for d, v in votes.items() if len(v) == len(models)}
    panel = {d: {"verdict": majority([v[m]["verdict"] for m in v]), "type": majority([v[m]["citation_type"] for m in v])}
             for d, v in full.items()}
    judged = [d for d, p in panel.items() if p["verdict"] in ("accurate", "minor", "major")]
    n = len(judged)
    maj = sum(panel[d]["verdict"] == "major" for d in judged)
    anyerr = sum(panel[d]["verdict"] in ("minor", "major") for d in judged)
    out = {"sampling": dict(status), "pairs_sampled": len(rows), "pairs_all_models": len(full), "models": models,
           "panel_verdicts": dict(collections.Counter(p["verdict"] for p in panel.values())),
           "primary_major": pct(maj, n), "secondary_any_error": pct(anyerr, n),
           "major_all_pairs_base": pct(maj, len(full)), "any_error_all_pairs_base": pct(anyerr, len(full))}
    out["per_model"] = {}
    for m in models:
        vs = [votes[d][m]["verdict"] for d in full]
        jd = [v for v in vs if v != "cannot_tell"]
        out["per_model"][m] = {"verdicts": dict(collections.Counter(vs)),
                               "major": pct(sum(v == "major" for v in jd), len(jd)),
                               "any_error": pct(sum(v in ("minor", "major") for v in jd), len(jd)),
                               "quote_found_share": round(usage[m]["quote_found"] / usage[m]["quotes"], 3) if usage[m]["quotes"] else None,
                               "lenient_parses": usage[m]["lenient"], "calls": usage[m]["calls"],
                               "neurons": round(usage[m]["neurons"], 1), "prompt_tokens": usage[m]["pt"], "completion_tokens": usage[m]["ct"]}
    pairs = {}
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            same = sum(full[d][a]["verdict"] == full[d][b]["verdict"] for d in full)
            pairs[f"{a.split('/')[-1]} vs {b.split('/')[-1]}"] = round(same / len(full), 3) if full else None
    out["agreement_pairwise"] = pairs
    out["fleiss_kappa_verdict"] = fleiss([[sum(full[d][m]["verdict"] == c for m in models) for c in VERDICTS] for d in full])
    out["unanimous_share"] = round(sum(len({full[d][m]["verdict"] for m in models}) == 1 for d in full) / len(full), 3) if full else None
    bytype = {}
    for t in ("specific_claim", "background", "method_or_tool", "data_source", "split"):
        ds = [d for d in judged if panel[d]["type"] == t]
        bytype[t] = {"n": len(ds), "major": pct(sum(panel[d]["verdict"] == "major" for d in ds), len(ds)),
                     "any_error": pct(sum(panel[d]["verdict"] in ("minor", "major") for d in ds), len(ds))}
    out["by_citation_type"] = bytype
    out["cited_retracted_pairs"] = sum(bool(rows[d].get("cited_retracted")) for d in rows)
    out["neurons_total"] = round(sum(u["neurons"] for u in usage.values()), 1)
    out["usd_at_list_neurons"] = round(out["neurons_total"] * 0.011 / 1000, 2)  # Workers AI: $0.011 per 1,000 neurons
    json.dump(out, open(sys.argv[3], "w") if len(sys.argv) > 3 else sys.stdout, indent=1)
    if len(sys.argv) > 3: print(json.dumps({k: out[k] for k in ("pairs_all_models", "primary_major", "secondary_any_error", "agreement_pairwise", "fleiss_kappa_verdict")}))


if __name__ == "__main__":
    main()
