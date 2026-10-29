#!/usr/bin/env python3
"""Scores the stage 3 rerun exactly as PREREG_RERUN_2026-10-22.md says: continuous P(major) per arm, leave one batch
out thresholds for the screen bar, AUCs, decide-alone kappas, bad parses, and Clef vs Jev with a paired bootstrap.

Usage: score_v3.py RUN_DIR [--arms a,b] [--json OUT.json] [--prices PRICES.json]
RUN_DIR holds <batch>/<arm>.jsonl from judge_v3.py; batches b2-b5 references are read from batches/.

Audit 22 Oct (code completion, no rule change; DEVIATIONS.md item 2): adds the pre-registered any-error AUC (score
P(major)+P(minor), votes when no logprobs) and cost per 1,000 citations (from a dated, sourced PRICES.json; no price
is written into this file, and with no price the cost is reported as not recorded, never as 0). An arm with a batch
absent or items missing is marked incomplete and pass_screen is None, not True/False. _rows keep full precision and
the bootstrap reports how many resamples were valid. Threshold rule, bars and P(major) scoring are unchanged."""
import argparse, glob, json, math, os, random

D = os.path.expanduser("work/checker")
BATCHES = ("b2", "b3", "b4", "b5")


def load_ref(b):
    if b == "b5":
        g = {}
        for f in sorted(glob.glob(f"{D}/batches/b5/ref/ref-*.jsonl")):
            for l in open(f):
                r = json.loads(l); g[r["draw"]] = r["verdict"]
        return g
    return {r["draw"]: r["verdict"] for r in map(json.loads, open(f"{D}/batches/{b}/gold/gold.jsonl"))}


def p_major(sample):
    lp = sample.get("lp")
    if isinstance(lp, dict) and "major" in lp:
        return float(lp["major"])
    return 1.0 if (sample.get("parsed") or {}).get("verdict") == "major" else 0.0


def p_error(sample):
    """P(major) + P(minor) from logprobs/probabilities when present, else 1 if the verdict is major or minor."""
    lp = sample.get("lp")
    if isinstance(lp, dict) and ("major" in lp or "minor" in lp):
        return float(lp.get("major", 0)) + float(lp.get("minor", 0))
    return 1.0 if (sample.get("parsed") or {}).get("verdict") in ("major", "minor") else 0.0


def majority(samples):
    """Top verdict: summed per-sample probabilities (or votes); ties go to the more severe verdict."""
    tot = {"accurate": 0.0, "minor": 0.0, "major": 0.0, "cannot_tell": 0.0}
    for s in samples:
        lp = s.get("lp")
        if isinstance(lp, dict) and lp:
            for k in tot: tot[k] += float(lp.get(k, 0))
        elif s.get("parsed"):
            tot[s["parsed"]["verdict"]] += 1
    order = ["major", "minor", "cannot_tell", "accurate"]
    return max(order, key=lambda k: (tot[k], -order.index(k)))


def load_arm(run, b, arm):
    f = f"{run}/{b}/{arm}.jsonl"
    if not os.path.exists(f):
        return None, {}
    last = {}
    for l in open(f):
        r = json.loads(l); last[r["draw"]] = r
    out, bad = {}, {"bad_samples": 0, "samples": 0, "cut_off": 0, "pt": 0, "ct": 0, "neurons": 0,
                    "discarded_samples": None}
    for d, r in last.items():
        sm = r.get("samples") or []
        bad["samples"] += max(1, len(sm))
        bad["bad_samples"] += sum(1 for s in sm if not s.get("parsed")) + (0 if sm else 1)
        bad["cut_off"] += sum(1 for s in sm if s.get("finish") == "length")
        bad["pt"] += (r.get("usage") or {}).get("pt") or 0
        bad["ct"] += (r.get("usage") or {}).get("ct") or 0
        bad["neurons"] += (r.get("usage") or {}).get("neurons") or 0
        if "discarded_samples" in r:  # written by judge_v3 only once it records retries; absent = not recorded
            bad["discarded_samples"] = (bad["discarded_samples"] or 0) + (r.get("discarded_samples") or 0)
        good = [s for s in sm if s.get("parsed")]
        if good:
            out[d] = (sum(p_major(s) for s in good) / len(good), majority(good),
                      sum(p_error(s) for s in good) / len(good))
    return out, bad


def auc(pos, neg):
    if not pos or not neg: return None
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def kappa(a, b):
    n = len(a)
    if n == 0: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def pick_threshold(rows, recall=0.90):
    """Highest t that catches >= recall of the majors in rows [(score, ref)]."""
    maj = sorted((s for s, g in rows if g == "major"), reverse=True)
    if not maj: return None
    need = math.ceil(recall * len(maj))
    return maj[need - 1]


def auc_error(rows):
    """Any error (reference major or minor) vs accurate, scored by P(error); other references are left out."""
    return auc([e for _, g, _, e in rows if g in ("major", "minor")], [e for _, g, _, e in rows if g == "accurate"])


def arm_cost(arm, model, meta, prices):
    """(usd, how) from PRICES.json, or (None, reason). A billing-record figure wins (e.g. Jev: AI Gateway record)."""
    if not prices:
        return None, "not recorded (no --prices file)"
    over = (prices.get("arm_cost_usd") or {}).get(arm)
    if over is not None:
        return float(over["usd"] if isinstance(over, dict) else over), "billing record"
    rate = (prices.get("per_model") or {}).get(model or "") or {}
    if rate.get("usd_per_1k_neurons") is not None and meta["neurons"]:
        return meta["neurons"] / 1000 * float(rate["usd_per_1k_neurons"]), "neurons x rate"
    if rate.get("usd_per_m_in") is not None and (meta["pt"] or meta["ct"]):
        usd = (meta["pt"] * float(rate["usd_per_m_in"]) + meta["ct"] * float(rate.get("usd_per_m_out") or 0)) / 1e6
        return usd, "tokens x rate"
    return None, f"not recorded (no price for {model})"


def arm_model(run, arm):
    for b in BATCHES:
        f = f"{run}/{b}/{arm}.jsonl"
        if os.path.exists(f):
            for l in open(f):
                return json.loads(l).get("model")
    return None


def score_arm(run, arm, prices=None):
    per = {}
    meta = {"bad_samples": 0, "samples": 0, "cut_off": 0, "pt": 0, "ct": 0, "neurons": 0, "discarded_samples": None,
            "items": 0, "missing": 0, "scored": 0}
    for b in BATCHES:
        ref = load_ref(b)
        got, bad = load_arm(run, b, arm)
        if got is None: continue
        for k in bad:
            if k == "discarded_samples":
                if bad[k] is not None: meta[k] = (meta[k] or 0) + bad[k]
            else:
                meta[k] += bad[k]
        judge = {d: g for d, g in ref.items() if g != "cannot_tell"}
        meta["items"] += len(judge)
        meta["missing"] += sum(1 for d in judge if d not in got)
        per[b] = [(got[d][0], g, got[d][1], got[d][2]) for d, g in judge.items() if d in got]
        meta["scored"] += len(per[b])
    absent = [b for b in BATCHES if b not in per]
    complete = not absent and meta["missing"] == 0
    why = [f"batches absent: {','.join(absent)}"] if absent else []
    if meta["missing"]: why.append(f"{meta['missing']} items missing")
    model = arm_model(run, arm)
    usd, how = arm_cost(arm, model, meta, prices)
    res = {"arm": arm, "model": model, **meta, "batches": sorted(per), "complete": complete,
           "incomplete_why": "; ".join(why) or None, "cost_usd": usd, "cost_how": how,
           "cost_per_1000": None if usd is None or not meta["scored"] else usd / meta["scored"] * 1000, "folds": {}}
    if len(per) < 2:
        return res
    caught = majors = flagged = total = 0
    for b in per:
        train = [(s, g) for o in per if o != b for s, g, _, _ in per[o]]
        t = pick_threshold(train)
        test = per[b]
        m = sum(1 for _, g, _, _ in test if g == "major")
        c = sum(1 for s, g, _, _ in test if g == "major" and t is not None and s >= t)
        f = sum(1 for s, _, _, _ in test if t is not None and s >= t)
        res["folds"][b] = {"t": t, "majors": m, "caught": c, "flagged": f, "n": len(test),
                           "auc_major": auc([s for s, g, _, _ in test if g == "major"], [s for s, g, _, _ in test if g != "major"]),
                           "auc_error": auc_error(test)}
        caught += c; majors += m; flagged += f; total += len(test)
    allrows = [x for b in per for x in per[b]]
    res["pooled"] = {"caught": caught, "majors": majors, "recall": round(caught / max(1, majors), 3),
                     "recall_ci": wilson(caught, majors), "flagged": flagged, "n": total,
                     "flag_rate": round(flagged / max(1, total), 3),
                     "pass_screen": (majors > 0 and caught / majors >= 0.90 and flagged / max(1, total) <= 0.50) if complete else None,
                     "status": "final" if complete else "partial",
                     "auc_major": auc([s for s, g, _, _ in allrows if g == "major"], [s for s, g, _, _ in allrows if g != "major"]),
                     "auc_error": auc_error(allrows),
                     "kappa_error": kappa([v in ("major", "minor") for _, _, v, _ in allrows], [g in ("major", "minor") for _, g, _, _ in allrows]),
                     "kappa_major": kappa([v == "major" for _, _, v, _ in allrows], [g == "major" for _, g, _, _ in allrows])}
    res["_rows"] = {b: [(s, g) for s, g, _, _ in per[b]] for b in per}  # full precision: rounded copies tie (amendment 6)
    return res


def paired_auc_diff(run, a1, a2, n=2000, seed=7, error=False):
    """Paired bootstrap AUC difference on shared items. error=False: major vs not-major by P(major) (the headline);
    error=True: any error vs accurate by P(error)."""
    rows = {}
    for b in BATCHES:
        ref = load_ref(b)
        g1, _ = load_arm(run, b, a1); g2, _ = load_arm(run, b, a2)
        if not g1 or not g2: continue
        for d, g in ref.items():
            if g != "cannot_tell" and d in g1 and d in g2:
                if not error:
                    rows[(b, d)] = (g1[d][0], g2[d][0], g == "major")
                elif g in ("major", "minor", "accurate"):
                    rows[(b, d)] = (g1[d][2], g2[d][2], g != "accurate")
    keys = list(rows); rnd = random.Random(seed); diffs = []

    def a(ks, i):
        return auc([rows[k][i] for k in ks if rows[k][2]], [rows[k][i] for k in ks if not rows[k][2]])
    base = (a(keys, 0), a(keys, 1))
    for _ in range(n):
        ks = [rnd.choice(keys) for _ in keys]
        x, y = a(ks, 0), a(ks, 1)
        if x is not None and y is not None: diffs.append(x - y)
    diffs.sort()
    return {"n_items": len(keys), "auc": base, "diff": round(base[0] - base[1], 3), "resamples": n, "valid_resamples": len(diffs),
            "ci95": (round(diffs[int(0.025 * len(diffs))], 3), round(diffs[int(0.975 * len(diffs))], 3)) if diffs else None}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--arms", default=""); ap.add_argument("--json", default="")
    ap.add_argument("--prices", default="", help="dated, sourced JSON: per_model {usd_per_1k_neurons | usd_per_m_in/out}, arm_cost_usd")
    a = ap.parse_args()
    prices = json.load(open(a.prices)) if a.prices else None
    arms = a.arms.split(",") if a.arms else sorted({os.path.basename(f)[:-6] for f in glob.glob(f"{a.run}/*/*.jsonl")})
    out = [score_arm(a.run, arm, prices) for arm in arms]
    print(f"{'arm':14} {'items':>5} {'miss':>4} {'bad':>4} {'cut':>4} {'caught/maj':>10} {'recall [CI]':>18} {'flag':>6} {'AUCmaj':>6} "
          f"{'AUCerr':>6} {'kErr':>6} {'kMaj':>6} {'$/1k':>7} pass")
    for r in out:
        p = r.get("pooled") or {}
        cpk = "n/r" if r.get("cost_per_1000") is None else f"{r['cost_per_1000']:.3f}"
        verdict = p.get("pass_screen") if r.get("complete") else f"PARTIAL ({r.get('incomplete_why')})"
        print(f"{r['arm']:14} {r['items']:>5} {r['missing']:>4} {r['bad_samples']:>4} {r['cut_off']:>4} "
              f"{str(p.get('caught'))+'/'+str(p.get('majors')):>10} {str(p.get('recall'))+' '+str(p.get('recall_ci')):>18} "
              f"{p.get('flag_rate')!s:>6} {(p.get('auc_major') or 0):6.3f} {(p.get('auc_error') or 0):6.3f} {p.get('kappa_error')!s:>6} "
              f"{p.get('kappa_major')!s:>6} {cpk:>7} {verdict}")
        for b, f in (r.get("folds") or {}).items():
            print(f"    {b}: t={f['t']} caught {f['caught']}/{f['majors']} flagged {f['flagged']}/{f['n']} AUC {f['auc_major']} AUCerr {f['auc_error']}")
    if "clef" in arms and "jev" in arms:
        print("Clef vs Jev AUC major (paired bootstrap):", paired_auc_diff(a.run, "clef", "jev"))
        print("Clef vs Jev AUC any error (paired bootstrap, secondary):", paired_auc_diff(a.run, "clef", "jev", error=True))
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
