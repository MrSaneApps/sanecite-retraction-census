#!/usr/bin/env python3
"""Try vote-combining rules over every 3-, 4- and 5-model panel against a reference; report the best by kappa.

Rules:
  plurality   v1 rule: a verdict needs 2 of 3 (or a strict majority); otherwise cannot_tell.
  twostep     error vs accurate by majority of the models that judged (cannot_tell abstains); if error, major when at
              least half of the error votes say major, else minor; no judging votes -> cannot_tell.
  any_k       error when at least k models say error (k = 1 or 2), severity as in twostep.
Usage: aggregate.py REF_GLOB JUDGED_DIR [--top 12] [--out OUT.json]"""
import argparse, collections, glob, itertools, json, os
import importlib.util

spec = importlib.util.spec_from_file_location("ev", os.path.join(os.path.dirname(__file__), "eval_ref.py"))
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)


def plurality(vs):
    c = collections.Counter(vs).most_common(1)[0]
    return c[0] if c[1] > len(vs) / 2 else "cannot_tell"


def severity(errs):
    return "major" if sum(v == "major" for v in errs) * 2 >= len(errs) else "minor"


def twostep(vs):
    judged = [v for v in vs if v != "cannot_tell"]
    if not judged: return "cannot_tell"
    errs = [v for v in judged if v in ("minor", "major")]
    if len(errs) * 2 > len(judged): return severity(errs)
    if len(errs) * 2 == len(judged): return "cannot_tell"
    return "accurate"


def any_k(k):
    def f(vs):
        errs = [v for v in vs if v in ("minor", "major")]
        if len(errs) >= k: return severity(errs)
        judged = [v for v in vs if v != "cannot_tell"]
        return "accurate" if judged else "cannot_tell"
    return f


RULES = {"plurality": plurality, "twostep": twostep, "any1": any_k(1), "any2": any_k(2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_glob"); ap.add_argument("judged")
    ap.add_argument("--top", type=int, default=12); ap.add_argument("--out", default="")
    a = ap.parse_args()
    ref = {}
    for f in sorted(glob.glob(a.ref_glob)):
        for l in open(f):
            j = json.loads(l); ref[j["draw"]] = j["verdict"]
    preds = {}
    for f in glob.glob(os.path.join(a.judged, "*.jsonl")):
        for l in open(f):
            j = json.loads(l)
            if j.get("parsed"): preds.setdefault(j["model"].split("/")[-1], {})[j["draw"]] = j["parsed"]["verdict"]
    names = sorted(preds)
    res = []
    for size in (3, 4, 5):
        for combo in itertools.combinations(names, size):
            common = set.intersection(*(set(preds[m]) for m in combo)) & set(ref)
            for rn, rule in RULES.items():
                agg = {d: rule([preds[m][d] for m in combo]) for d in common}
                s = ev.scores(ref, agg)
                res.append({"panel": "+".join(combo), "size": size, "rule": rn, **s})
    key = lambda r: (r["kappa_error"] or 0) + (r["kappa_major"] or 0)
    res.sort(key=key, reverse=True)
    if a.out: json.dump(res, open(a.out, "w"))
    for r in res[: a.top]:
        print(f"{r['rule']:9} {r['size']} {r['panel'][:110]:110} kErr={r['kappa_error']} kMaj={r['kappa_major']} k4={r['kappa4']} "
              f"maj%={r['pred_major_rate']} err%={r['pred_error_rate']} ct={r['pred_cannot_tell']}")
    for size in (3, 4, 5):
        best = max((r for r in res if r["size"] == size), key=key)
        print("BEST", size, best["rule"], best["panel"], "kErr", best["kappa_error"], "kMaj", best["kappa_major"])


if __name__ == "__main__":
    main()
