#!/usr/bin/env python3
"""Apply the PREREG_SYSTEM_2026-10-22 choice rule (steps 1-5, amendment 2) to the complete batch 2-5 rerun and write
SYSTEM_LOCKED_2026-10-22.json / .md. No model calls.

Rule: candidates = every screen arm x every decider set (each thinking arm alone; majority of deepseek_on, qwen_on,
glm_on; majority sets that include kimi_on). Leave-one-batch-out thresholds (90% recall of reference majors) score
each combination on batches 2-5. Eligible: screen flags <= 50%. Pick the highest kappa_major; ties within 0.01 go to
the lower cost per 1,000 citations. Amendment 2: the screen is Clef unless the best Jev system beats the best Clef
system with the same deciders by a meaningful margin (paired bootstrap 95% CI of the kappa_major difference excludes 0,
or Jev catches >= 3 more majors at no lower precision); the other becomes the secondary system.
The locked screen threshold is the 90%-recall cut on all four batches pooled.

Usage: lock_system.py RUN_DIR"""
import hashlib, itertools, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_v3 as s

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = ["jev", "clef", "qwen_off", "glm_off", "gptoss_med", "deepseek_off", "gemma_off", "kimi_off"]
THINK = ["deepseek_on", "qwen_on", "glm_on", "gemma_on", "gptoss_high", "kimi_on"]
DEC_SETS = [(d,) for d in THINK] + [("deepseek_on", "qwen_on", "glm_on")] + \
    [c for c in itertools.combinations(["deepseek_on", "qwen_on", "glm_on", "kimi_on"], 3) if "kimi_on" in c]
# cost per 1,000 citations, $, from Cloudflare billed usage 22 Oct 10:00-19:00 UTC divided by citations judged per arm
# (approximate; only used to break ties within 0.01 kappa)
COST = {"deepseek_on": 2.5, "qwen_on": 7.0, "glm_on": 7.5, "kimi_on": 15.0, "gemma_on": 1.5, "gptoss_high": 4.0}


def vote(vs):
    order = ["major", "minor", "accurate", "cannot_tell"]
    return max(order, key=lambda k: (vs.count(k), -order.index(k)))


def rows_for(arms, refs, sc, ds):
    out = {}
    for b in s.BATCHES:
        out[b] = [d for d in refs[b] if d in arms[sc][b] and all(d in arms[x][b] for x in ds)]
    return out


def evaluate(arms, refs, sc, ds, per):
    rec = []
    for b in s.BATCHES:
        train = [(arms[sc][o][d][0], refs[o][d]) for o in s.BATCHES if o != b for d in per[o]]
        t = s.pick_threshold(train)
        for d in per[b]:
            g = refs[b][d]; fl = t is not None and arms[sc][b][d][0] >= t
            v = vote([arms[x][b][d][1] for x in ds]) if fl else "accurate"
            rec.append((b, d, fl, v == "major", g == "major"))
    return rec


def summary(rec):
    n = len(rec); maj = sum(r[4] for r in rec); calls = sum(r[3] for r in rec); tp = sum(r[3] and r[4] for r in rec)
    return {"n": n, "majors": maj, "caught": tp, "flag_rate": round(sum(r[2] for r in rec) / n, 3), "major_calls": calls,
            "precision": round(tp / calls, 3) if calls else None,
            "kappa_major": s.kappa([r[3] for r in rec], [r[4] for r in rec])}


def boot_diff(r1, r2, n=2000, seed=7):
    k1 = {(b, d): (p, g) for b, d, _, p, g in r1}; k2 = {(b, d): (p, g) for b, d, _, p, g in r2}
    keys = sorted(set(k1) & set(k2)); rng = random.Random(seed); diffs = []
    for _ in range(n):
        smp = [keys[rng.randrange(len(keys))] for _ in keys]
        a = s.kappa([k1[k][0] for k in smp], [k1[k][1] for k in smp]); c = s.kappa([k2[k][0] for k in smp], [k2[k][1] for k in smp])
        if a is not None and c is not None: diffs.append(a - c)
    diffs.sort()
    return (round(diffs[int(.025 * len(diffs))], 3), round(diffs[int(.975 * len(diffs))], 3))


def main():
    run = sys.argv[1]
    refs = {b: {d: g for d, g in s.load_ref(b).items() if g != "cannot_tell"} for b in s.BATCHES}
    arms = {x: {b: (s.load_arm(run, b, x)[0] or {}) for b in s.BATCHES} for x in SCREENS + THINK}
    table = []
    for sc in SCREENS:
        for ds in DEC_SETS:
            per = rows_for(arms, refs, sc, ds)
            if sum(map(len, per.values())) < 550: continue
            rec = evaluate(arms, refs, sc, ds, per)
            table.append({"screen": sc, "deciders": list(ds), "cost": round(sum(COST[x] for x in ds), 1), **summary(rec), "_rec": rec})
    allelig = [r for r in table if r["flag_rate"] <= 0.50 and r["kappa_major"] is not None]
    allelig.sort(key=lambda r: (-r["kappa_major"], r["cost"]))
    # Amendment 2, as written: the screen is Clef unless Jev is meaningfully better; choose deciders behind Clef.
    elig = [r for r in allelig if r["screen"] == "clef"]
    elig.sort(key=lambda r: (-r["kappa_major"], r["cost"]))
    top = elig[0]
    ties = [r for r in elig if top["kappa_major"] - r["kappa_major"] <= 0.01]
    best = min(ties, key=lambda r: (r["cost"], -r["kappa_major"]))
    ds = best["deciders"]
    clef = next((r for r in table if r["screen"] == "clef" and r["deciders"] == ds), None)
    jev = next((r for r in table if r["screen"] == "jev" and r["deciders"] == ds), None)
    decision = {"rule_pick": {k: best[k] for k in ("screen", "deciders", "kappa_major", "caught", "majors", "precision", "flag_rate")}}
    if best["screen"] in ("clef", "jev") and clef and jev:
        ci = boot_diff(jev["_rec"], clef["_rec"])
        more = jev["caught"] - clef["caught"]
        jev_meaningful = (ci[0] > 0) or (more >= 3 and (jev["precision"] or 0) >= (clef["precision"] or 0))
        primary, secondary = (jev, clef) if jev_meaningful else (clef, jev)
        decision["amendment2"] = {"jev_minus_clef_kappa_ci95": ci, "jev_extra_majors": more, "jev_meaningfully_better": jev_meaningful}
    else:
        primary = best
        secondary = clef if clef and best["screen"] != "clef" else jev
        decision["amendment2"] = "rule pick screen is neither Clef nor Jev; Clef-screen system is secondary"
        if best["screen"] != "clef" and clef: secondary = clef
    def lock(r):
        pooled = [(arms[r["screen"]][b][d][0], refs[b][d]) for b in s.BATCHES for d in rows_for(arms, refs, r["screen"], r["deciders"])[b]]
        return {"screen": r["screen"], "deciders": r["deciders"], "rule": "majority vote of deciders on flagged; unflagged = not major",
                "threshold_p_major": s.pick_threshold(pooled), "b2_b5": {k: r[k] for k in ("n", "majors", "caught", "precision", "flag_rate", "kappa_major")}}
    cfg = os.path.join(D, "model-cards", "configs.json")
    out = {"locked_at_note": "written before any model call on batch 6", "primary": lock(primary), "secondary": lock(secondary),
           "decision": decision, "configs_sha256": hashlib.sha256(open(cfg, "rb").read()).hexdigest(),
           "exploratory_best_any_screen": lock(allelig[0]) if allelig[0]["screen"] not in ("clef", "jev") else None,
           "top10_any_screen": [{k: r[k] for k in ("screen", "deciders", "kappa_major", "caught", "majors", "precision", "flag_rate", "cost")} for r in allelig[:10]]}
    json.dump(out, open(os.path.join(D, "SYSTEM_LOCKED_2026-10-22.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("primary", "secondary", "decision")}, indent=1))
    for r in out["top10_any_screen"]: print(r)


if __name__ == "__main__":
    main()
