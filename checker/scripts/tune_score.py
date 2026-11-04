#!/usr/bin/env python3
"""Score readers and screen -> decider systems (TUNING_CURSOR_ANTHROPIC_2026-10-30.md).

Readers come from batches/<b>/cursor/*.jsonl and batches/<b>/anthropic/*.jsonl (b2-b5 tuning set) and
batches/b6/cursor/full/*.jsonl + batches/b6/anthropic/*.jsonl (batch 6). References: score_v3.load_ref (b2-b5) and
batches/b6/gold/gold.jsonl. "cannot_tell" references are left out, as in the locked system's scoring.

A system: screen reader S flags an item when its verdict is in FLAG (major, or major/minor); flagged items go to
the deciders, and the system calls major when at least NEED of them say major. Unflagged = not major.
Bars (PREREG_SYSTEM_2026-10-22): kappa_major >= 0.60, recall >= 0.70, precision >= 0.65, judged on b2-b5.

usage: tune_score.py [--quiet-model NAME] [--top 15] [--out logs/tune_score.json]"""
import argparse, glob, itertools, json, math, os, sys

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(D, "scripts"))
import score_v3  # noqa: E402

TUNE = ("b2", "b3", "b4", "b5")
SETS = {"tune": TUNE, "b6": ("b6",)}
BARS = {"kappa_major": 0.60, "recall": 0.70, "precision": 0.65}


def refs():
    r = {}
    for b in TUNE:
        for d, v in score_v3.load_ref(b).items():
            r[(b, d)] = v
    for l in open(os.path.join(D, "batches/b6/gold/gold.jsonl")):
        j = json.loads(l)
        r[("b6", j["draw"])] = j["verdict"]
    return r


def readers():
    out, usage = {}, {}
    pats = [(b, f"batches/{b}/cursor/*.jsonl") for b in TUNE] + [(b, f"batches/{b}/anthropic/*.jsonl") for b in TUNE + ("b6",)]
    pats.append(("b6", "batches/b6/cursor/full/*.jsonl"))
    for b, pat in pats:
        for f in glob.glob(os.path.join(D, pat)):
            for l in open(f):
                j = json.loads(l)
                m = j["model"]
                if j.get("parsed"):
                    out.setdefault(m, {})[(b, j["draw"])] = j["parsed"]["verdict"]
                u = j.get("usage") or {}
                acc = usage.setdefault(m, {"calls": 0, "tokens": 0.0, "usd": 0.0})
                acc["calls"] += 1
                acc["tokens"] += sum(float(u.get(k) or 0) for k in ("inputTokens", "outputTokens", "cacheReadTokens",
                                                                    "input_tokens", "output_tokens",
                                                                    "cache_creation_input_tokens", "cache_read_input_tokens"))
                acc["usd"] += float(j.get("usd") or 0)
    return out, usage


def kappa(a, b):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def wilson_lo(k, n, z=1.96):
    if not n:
        return 0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def metrics(ref, calls, keys):
    """calls: key -> 'major' or other; keys: the items to score (reference judged, call present)."""
    r = ["maj" if ref[k] == "major" else "no" for k in keys]
    p = ["maj" if calls[k] == "major" else "no" for k in keys]
    tp = sum(x == y == "maj" for x, y in zip(r, p))
    nr, npred = r.count("maj"), p.count("maj")
    m = {"n": len(keys), "majors": nr, "caught": tp, "called": npred,
         "recall": round(tp / nr, 3) if nr else None, "precision": round(tp / npred, 3) if npred else None,
         "kappa_major": kappa(r, p), "recall_lo95": round(wilson_lo(tp, nr), 3) if nr else None}
    m["pass"] = all((m[k] or 0) >= v for k, v in BARS.items())
    return m


def single(ref, rd, set_name):
    keys = [k for k in ref if k[0] in SETS[set_name] and ref[k] != "cannot_tell" and k in rd]
    return metrics(ref, rd, keys)


def system(ref, R, screen, flag, deciders, need, set_name):
    keys = [k for k in ref if k[0] in SETS[set_name] and ref[k] != "cannot_tell" and k in R[screen]
            and all(k in R[d] for d in deciders)]
    calls = {}
    for k in keys:
        if R[screen][k] in flag:
            calls[k] = "major" if sum(R[d][k] == "major" for d in deciders) >= need else "no"
        else:
            calls[k] = "no"
    m = metrics(ref, calls, keys)
    m["flag_rate"] = round(sum(R[screen][k] in flag for k in keys) / max(len(keys), 1), 3)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet-model", default=""); ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--out", default=os.path.join(D, "logs/tune_score.json"))
    a = ap.parse_args()
    ref = refs()
    R, U = readers()
    res = {"singles": {}, "systems": []}
    for m, rd in sorted(R.items()):
        res["singles"][m] = {s: single(ref, rd, s) for s in SETS}
        res["singles"][m]["usage"] = U.get(m)
        if not a.quiet_model or m == a.quiet_model:
            for s in SETS:
                print("MODEL", m, s, json.dumps(res["singles"][m][s]))
    if a.quiet_model:
        json.dump(res, open(a.out, "w"), indent=1)
        return
    names = [m for m in R if res["singles"][m]["tune"]["n"] >= 400]
    for screen in names:
        for flag in (("major",), ("major", "minor")):
            others = [m for m in names if m != screen]
            for size in (1, 2, 3):
                for dec in itertools.combinations(others, size):
                    for need in range(1, size + 1):
                        if size >= 2 and need < (size + 1) // 2:
                            continue
                        t = system(ref, R, screen, flag, dec, need, "tune")
                        if t["n"] < 400:
                            continue
                        b6 = system(ref, R, screen, flag, dec, need, "b6")
                        res["systems"].append({"screen": screen, "flag": "+".join(flag), "deciders": list(dec),
                                               "need": need, "tune": t, "b6": b6})
    ok = [s for s in res["systems"] if s["tune"]["pass"]]
    ok.sort(key=lambda s: (-(s["tune"]["kappa_major"] or 0)))
    print(f"systems scored {len(res['systems'])}, passing on b2-b5: {len(ok)}")
    for s in ok[:a.top]:
        print("SYSTEM", s["screen"], s["flag"], "->", "+".join(s["deciders"]), f"need {s['need']}",
              "tune", {k: s["tune"][k] for k in ("recall", "precision", "kappa_major", "flag_rate")},
              "b6", {k: s["b6"][k] for k in ("recall", "precision", "kappa_major")})
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
