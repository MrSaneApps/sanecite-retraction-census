#!/usr/bin/env python3
"""EXPLORATORY (chosen after seeing the rerun results; not a confirmatory test). Simulates a two-stage system on the
rerun data: a screen arm flags citations with P(major) >= a leave-one-batch-out threshold (same rule as score_v3), then
a decider arm (or a majority of several) gives the final verdict on flagged citations; unflagged count as not major.
Reports per combination: majors caught by the system, system flags, kappa_major vs reference on all items,
precision of final major calls. Usage: two_stage_explore.py RUN_DIR [--json OUT]"""
import argparse, itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_v3 as s

SCREENS = ["jev", "clef", "qwen_off", "glm_off", "gptoss_med", "deepseek_off", "gemma_off", "kimi_off"]
DECIDERS = ["deepseek_on", "qwen_on", "glm_on", "gemma_on", "gptoss_high", "kimi_on"]


def load(run, arm):
    return {b: (s.load_arm(run, b, arm)[0] or {}) for b in s.BATCHES}


def vote(vs):
    order = ["major", "minor", "accurate", "cannot_tell"]
    return max(order, key=lambda k: (vs.count(k), -order.index(k)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--json", default="")
    a = ap.parse_args()
    refs = {b: {d: g for d, g in s.load_ref(b).items() if g != "cannot_tell"} for b in s.BATCHES}
    arms = {x: load(a.run, x) for x in SCREENS + DECIDERS}
    out = []
    dec_sets = [(d,) for d in DECIDERS] + list(itertools.combinations(["deepseek_on", "qwen_on", "glm_on"], 3))
    for sc in SCREENS:
        for ds in dec_sets:
            # common items: screen and every decider have a result
            per = {}
            for b in s.BATCHES:
                per[b] = [d for d in refs[b] if d in arms[sc][b] and all(d in arms[x][b] for x in ds)]
            if sum(map(len, per.values())) < 400: continue
            caught = majors = flagged = called = tp = n = 0; sysv, refv = [], []
            for b in s.BATCHES:
                train = [(arms[sc][o][d][0], refs[o][d]) for o in s.BATCHES if o != b for d in per[o]]
                t = s.pick_threshold(train)
                for d in per[b]:
                    g = refs[b][d]; n += 1; majors += g == "major"
                    fl = t is not None and arms[sc][b][d][0] >= t
                    flagged += fl
                    v = vote([arms[x][b][d][1] for x in ds]) if fl else "accurate"
                    sysv.append(v == "major"); refv.append(g == "major")
                    if v == "major":
                        called += 1; tp += g == "major"
                    caught += (v == "major" and g == "major")
            out.append({"screen": sc, "decider": "+".join(ds), "n": n, "majors": majors, "caught": caught,
                        "flag_rate": round(flagged / n, 3), "major_calls": called,
                        "precision": round(tp / called, 3) if called else None,
                        "kappa_major": s.kappa(sysv, refv)})
    # deciders alone, for comparison
    for ds in dec_sets:
        sysv, refv = [], []; caught = majors = called = tp = 0
        for b in s.BATCHES:
            for d, g in refs[b].items():
                if not all(d in arms[x][b] for x in ds): continue
                v = vote([arms[x][b][d][1] for x in ds]); sysv.append(v == "major"); refv.append(g == "major")
                majors += g == "major"; caught += v == "major" and g == "major"; called += v == "major"; tp += v == "major" and g == "major"
        out.append({"screen": "(none)", "decider": "+".join(ds), "n": len(sysv), "majors": majors, "caught": caught,
                    "flag_rate": 1.0, "major_calls": called, "precision": round(tp / called, 3) if called else None,
                    "kappa_major": s.kappa(sysv, refv)})
    out.sort(key=lambda r: -(r["kappa_major"] or -1))
    print(f"{'screen':13}{'decider':30}{'n':>5}{'caught':>10}{'flag':>7}{'calls':>7}{'prec':>7}{'kMaj':>7}")
    for r in out[:40]:
        print(f"{r['screen']:13}{r['decider']:30}{r['n']:5}{str(r['caught'])+'/'+str(r['majors']):>10}{r['flag_rate']:7}{r['major_calls']:7}{str(r['precision']):>7}{str(r['kappa_major']):>7}")
    if a.json: json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
