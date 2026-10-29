#!/usr/bin/env python3
"""Score the locked system on batch 6 against the adjudicated reference (PREREG_SYSTEM_2026-10-22, primary bars:
kappa_major >= 0.60, recall of reference majors >= 0.70, precision of major calls >= 0.65). Also: secondary system,
flag rate, system vs reference major rate, kappa for any error on flagged items, reader agreement (the ceiling), and the
amendment-4/5 sensitivity (Gemini in place of Grok as reader A for the 66 items).

Usage: score_b6.py RUN_DIR  (reads SYSTEM_LOCKED_2026-10-22.json and batches/b6/gold)"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_v3 as s

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B6 = os.path.join(D, "batches", "b6")


def vote(vs):
    order = ["major", "minor", "accurate", "cannot_tell"]
    return max(order, key=lambda k: (vs.count(k), -order.index(k)))


def load_gold(path):
    return {json.loads(l)["draw"]: json.loads(l)["verdict"] for l in open(path)}


def system_calls(run, lock):
    scr, _ = s.load_arm(run, "b6", lock["screen"])
    decs = {x: s.load_arm(run, "b6", x)[0] for x in lock["deciders"]}
    t = lock["threshold_p_major"]
    calls, flagged, missing = {}, set(), 0
    for d, v in scr.items():
        p = v[0]
        if p >= t:
            flagged.add(d)
            vs = [decs[x][d][1] for x in lock["deciders"] if d in decs[x]]
            if len(vs) < len(lock["deciders"]): missing += 1
            calls[d] = vote(vs) if vs else "major"
        else:
            calls[d] = "accurate"
    return calls, flagged, missing


def bars(calls, gold, flagged):
    items = [d for d, g in gold.items() if g != "cannot_tell" and d in calls]
    sysm = [calls[d] == "major" for d in items]; refm = [gold[d] == "major" for d in items]
    maj = sum(refm); tp = sum(a and b for a, b in zip(sysm, refm)); n_calls = sum(sysm)
    km = s.kappa(sysm, refm)
    rec = tp / maj if maj else None; prec = tp / n_calls if n_calls else None
    fl_items = [d for d in items if d in flagged]
    ke = s.kappa([calls[d] in ("major", "minor") for d in fl_items], [gold[d] in ("major", "minor") for d in fl_items]) if fl_items else None
    return {"n": len(items), "ref_majors": maj, "caught": tp, "major_calls": n_calls,
            "recall": round(rec, 3) if rec is not None else None, "recall_ci95": s.wilson(tp, maj),
            "precision": round(prec, 3) if prec is not None else None, "precision_ci95": s.wilson(tp, n_calls),
            "kappa_major": km, "flag_rate": round(sum(1 for d in items if d in flagged) / len(items), 3),
            "system_major_rate": round(n_calls / len(items), 4), "ref_major_rate": round(maj / len(items), 4),
            "ref_major_rate_ci95": s.wilson(maj, len(items)), "kappa_error_on_flagged": ke,
            "PASS": bool(km is not None and km >= 0.60 and rec is not None and rec >= 0.70 and prec is not None and prec >= 0.65)}


def main():
    run = sys.argv[1]
    lock = json.load(open(os.path.join(D, "SYSTEM_LOCKED_2026-10-22.json")))
    gold = load_gold(os.path.join(B6, "gold", "gold.jsonl"))
    out = {}
    for which in ("primary", "secondary"):
        calls, flagged, missing = system_calls(run, lock[which])
        out[which] = {"system": f"{lock[which]['screen']} screen -> {'+'.join(lock[which]['deciders'])}", "missing_decider_votes": missing,
                      **bars(calls, gold, flagged)}
    # sensitivity: Gemini replaces Grok as reader A for the 66 Claude-stop items (gold rebuilt the same way)
    sens = os.path.join(B6, "gold_gemini", "gold.jsonl")
    if os.path.exists(sens):
        g2 = load_gold(sens)
        calls, flagged, _ = system_calls(run, lock["primary"])
        out["primary_with_gemini_reader"] = bars(calls, g2, flagged)
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(D, "B6_RESULT_2026-10-22.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
