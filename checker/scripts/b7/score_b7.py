#!/usr/bin/env python3
"""Score the batch 7 answer key once (PREREG_REFSET_B7 section 7). Run on batch 6 first as the test: it must give
66 of 915 major, 186 of 915 any error and a ceiling of 0.658.

Measures (Part A): coverage; judged and major counts; the ceiling (reader 1 vs Muse kappa_major on items where
neither said cannot_tell); major and any-error rates with Wilson 95% intervals; the pooling rule (90% Newcombe
interval for batch 7 minus batch 6 inside +/-3.0 points, canary at least 28 of 33, ceiling at least 0.60) and the
pooled figure; specific_claim vs background major rates (Newcombe 95%); sensitivities (without fallback-read items,
without Grok-adjudicated items, 2-of-3 blind majority if the third reads exist); each reader's agreement with the
key by model. Optional: the frozen system's scores against the key (--system), with the maker-overlap checks.

usage: score_b7.py --batch b6|b7 [--canary FILE.jsonl] [--system SCREEN.jsonl DEC1.jsonl DEC2.jsonl DEC3.jsonl]
                   [--out FILE.json]"""
import argparse, glob, json, math, os, sys

D = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(D, "scripts"))
import score_v3 as s  # noqa: E402

LAYOUT = {
    "b6": {"a": ["batches/b6/ref_A/readerA.jsonl"], "muse": "batches/b6/ref_muse/muse.jsonl",
           "gold": "batches/b6/gold/gold.jsonl", "adj": "batches/b6/gold/adjudicated.jsonl",
           "sample": "batches/b6/sample_test.jsonl", "third": None},
    "b7": {"a": "batches/b7/ref_claude/ref-*.jsonl", "muse": "batches/b7/muse/muse.jsonl",
           "gold": "batches/b7/gold/gold.jsonl", "adj": "batches/b7/adj/adjudicated.jsonl",
           "sample": "batches/b7/sample_read.jsonl", "third": "batches/b7/adj/third-gemini-*.jsonl"},
}
Z90, Z95 = 1.6449, 1.96


def jl(fn):
    out = []
    for l in open(fn):
        try:
            out.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    return out


def files(spec):
    if spec is None:
        return []
    if isinstance(spec, list):
        return [os.path.join(D, f) for f in spec]
    return sorted(glob.glob(os.path.join(D, spec)))


def wilson(k, n, z=Z95):
    if not n:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 4), round(c + h, 4)]


def newcombe(k1, n1, k2, n2, z):
    """Newcombe hybrid score interval for p1 - p2."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return round(d, 4), [round(lo, 4), round(hi, 4)]


def rate(keys, key, what):
    k = sum(key[d]["verdict"] in what for d in keys)
    return {"k": k, "n": len(keys), "rate": round(k / len(keys), 4) if keys else None, "ci95": wilson(k, len(keys))}


def load(batch):
    L = LAYOUT[batch]
    a = {}
    for f in files(L["a"]):
        for j in jl(f):
            a[j["draw"]] = j
    mu = {j["draw"]: j["parsed"] for j in jl(os.path.join(D, L["muse"])) if j.get("parsed")}
    key = {j["draw"]: j for j in jl(os.path.join(D, L["gold"]))}
    adj = {j["draw"]: j for j in jl(os.path.join(D, L["adj"]))} if os.path.exists(os.path.join(D, L["adj"])) else {}
    n_sample = sum(1 for j in jl(os.path.join(D, L["sample"])) if j.get("status") == "ok")
    third = {}
    for f in files(L["third"]):
        for j in jl(f):
            # gemini_read.py / openrouter_read.py write the verdict at the top level; older readers nest it in "parsed".
            v = (j.get("parsed") or {}).get("verdict") or j.get("verdict")
            if v:
                third[j["draw"]] = v
    return a, mu, key, adj, n_sample, third


def reader_model(row):
    return row.get("model") or row.get("reader") or "unknown"


def part_a(batch, canary_file=None):
    a, mu, key, adj, n_sample, third = load(batch)
    judged = sorted(d for d in key if key[d]["verdict"] != "cannot_tell")
    both = [d for d in sorted(set(a) & set(mu)) if a[d]["verdict"] != "cannot_tell" and mu[d]["verdict"] != "cannot_tell"]
    ceiling = s.kappa([a[d]["verdict"] == "major" for d in both], [mu[d]["verdict"] == "major" for d in both])
    out = {"batch": batch, "reading_set": n_sample, "keyed": len(key),
           "coverage": round(len(key) / n_sample, 4) if n_sample else None, "judged": len(judged),
           "major": rate(judged, key, ("major",)), "any_error": rate(judged, key, ("major", "minor")),
           "ceiling_kappa_major": ceiling, "ceiling_items": len(both)}
    # citation type, by the key's citation_type
    ct = {}
    for t in ("specific_claim", "background", "method_or_tool", "data_source"):
        ks = [d for d in judged if key[d].get("citation_type") == t]
        ct[t] = rate(ks, key, ("major",))
    sc, bg = ct["specific_claim"], ct["background"]
    if sc["n"] and bg["n"]:
        ct["specific_minus_background_95"] = newcombe(sc["k"], sc["n"], bg["k"], bg["n"], Z95)
    out["by_citation_type"] = ct
    # sensitivities
    claude_rows = {d for d in a if "claude" in reader_model(a[d]).lower()}
    no_fb = [d for d in judged if d in claude_rows]
    out["without_fallback_items"] = {"major": rate(no_fb, key, ("major",)), "any_error": rate(no_fb, key, ("major", "minor"))}
    grok_adj = {d for d, j in adj.items() if "grok" in str(j.get("adjudicator", "")).lower()}
    no_grok = [d for d in judged if d not in grok_adj]
    out["without_grok_adjudicated"] = {"items_removed": len(grok_adj & set(judged)), "major": rate(no_grok, key, ("major",))}
    if third:
        dis = [d for d in key if key[d].get("source") == "adjudicated" and d in third and d in a and d in mu]
        maj = {}
        for d in dis:
            vs = [a[d]["verdict"], mu[d]["verdict"], third[d]]
            top = max(set(vs), key=vs.count)
            maj[d] = top if vs.count(top) >= 2 else "cannot_tell"
        differ = sum(maj[d] != key[d]["verdict"] for d in dis)
        out["two_of_three"] = {"disagreement_items": len(dis), "differ_from_key": differ,
                               "differ_share": round(differ / len(dis), 3) if dis else None,
                               "report_both_ways": bool(dis and differ / len(dis) > 0.15)}
    # each reader's agreement with the key, by model
    by = {}
    for d in judged:
        if d in a:
            m = reader_model(a[d])
            x = by.setdefault(m, [0, 0]); x[0] += a[d]["verdict"] == key[d]["verdict"]; x[1] += 1
        if d in mu:
            x = by.setdefault("muse", [0, 0]); x[0] += mu[d]["verdict"] == key[d]["verdict"]; x[1] += 1
    out["reader_agreement_with_key"] = {m: {"agree": v[0], "n": v[1], "share": round(v[0] / v[1], 3)} for m, v in by.items()}
    if canary_file:
        g6 = {j["draw"]: j["verdict"] for j in jl(os.path.join(D, LAYOUT["b6"]["gold"]))}
        rows = [j for j in jl(canary_file) if j.get("parsed")]
        out["canary"] = {"read": len(rows), "match_b6_gold": sum(j["parsed"]["verdict"] == g6.get(j["draw"]) for j in rows)}
    return out, key


def pooling(b7, b6, canary_ok):
    m7, m6 = b7["major"], b6["major"]
    diff, ci90 = newcombe(m7["k"], m7["n"], m6["k"], m6["n"], Z90)
    pooled_k, pooled_n = m7["k"] + m6["k"], m7["n"] + m6["n"]
    rules = {"equivalence_inside_3pts": -0.03 <= ci90[0] and ci90[1] <= 0.03,
             "canary_28_of_33": canary_ok, "ceiling_0.60": (b7["ceiling_kappa_major"] or 0) >= 0.60}
    return {"b7_minus_b6": diff, "ci90": ci90, "rules": rules, "pool": all(rules.values()),
            "pooled_major": {"k": pooled_k, "n": pooled_n, "rate": round(pooled_k / pooled_n, 4), "ci95": wilson(pooled_k, pooled_n)}}


def system_scores(key, a, mu, screen_f, dec_fs):
    def calls(fn):
        return {j["draw"]: j["parsed"]["verdict"] for j in jl(fn) if j.get("parsed")}
    scr = calls(screen_f)
    decs = [calls(f) for f in dec_fs]
    sysc = {d: ("major" if scr.get(d) == "major" and any(x.get(d) == "major" for x in decs) else "no") for d in scr}

    def score(ref, keys):
        r = [ref[d] == "major" for d in keys]; p = [sysc[d] == "major" for d in keys]
        tp = sum(x and y for x, y in zip(r, p)); nr, npd = sum(r), sum(p)
        m = {"n": len(keys), "majors": nr, "caught": tp, "called": npd,
             "recall": round(tp / nr, 3) if nr else None, "recall_ci95": wilson(tp, nr) if nr else None,
             "precision": round(tp / npd, 3) if npd else None, "kappa_major": s.kappa(r, p)}
        m["pass"] = bool((m["kappa_major"] or 0) >= 0.60 and (m["recall"] or 0) >= 0.70 and (m["precision"] or 0) >= 0.65)
        return m
    ref = {d: key[d]["verdict"] for d in key}
    judged = [d for d in key if ref[d] != "cannot_tell" and d in sysc]
    agreed = [d for d in judged if key[d].get("source") == "agree"]
    mref = {d: mu[d]["verdict"] for d in mu}
    muse_only = [d for d in judged if d in mref and mref[d] != "cannot_tell"]
    return {"primary": score(ref, judged),
            "agreed_items_only (no adjudicator)": score(ref, agreed),
            "against_muse_alone (non-Claude reader)": score(mref, muse_only),
            "flag_rate": round(sum(scr.get(d) == "major" for d in judged) / len(judged), 3) if judged else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True, choices=sorted(LAYOUT))
    ap.add_argument("--canary"); ap.add_argument("--system", nargs=4); ap.add_argument("--out")
    x = ap.parse_args()
    res, key = part_a(x.batch, x.canary)
    if x.batch == "b7":
        b6, _ = part_a("b6")
        c = res.get("canary", {})
        # Section 3: at least 28 of the 33 canary items match batch 6 gold; a refused canary item counts as a miss.
        res["pooling"] = pooling(res, b6, c.get("match_b6_gold", 0) >= 28)
    if x.system:
        a, mu, *_ = load(x.batch)
        res["system"] = system_scores(key, a, mu, x.system[0], x.system[1:])
    print(json.dumps(res, indent=1))
    if x.out:
        json.dump(res, open(x.out, "w"), indent=1)


if __name__ == "__main__":
    main()
