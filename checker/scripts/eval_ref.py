#!/usr/bin/env python3
"""Score every model (and candidate panels) against a blind reference read.

Usage: eval_ref.py REF_GLOB JUDGED_DIR [--panels "a,b,c;a,b,d"] [--out OUT.json]
REF_GLOB: reference jsonl files ({"draw", "verdict", "citation_type"}). JUDGED_DIR: per-model jsonl from judge_v2.py.
Reports, per model and per panel (majority of 3; no majority = split, counted as cannot_tell): exact agreement and
Cohen's kappa on the four verdicts, kappa on error (minor or major) vs accurate, kappa on major vs not, and the
model's own major and any-error rates, on the pairs where the reference could judge."""
import argparse, collections, glob, itertools, json, os

V = ("accurate", "minor", "major", "cannot_tell")


def kappa(a, b, cats):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def scores(ref, pred):
    ds = [d for d in ref if d in pred]
    r = [ref[d] for d in ds]; p = [pred[d] for d in ds]
    judged = [i for i, x in enumerate(r) if x != "cannot_tell"]
    rb = ["err" if r[i] in ("minor", "major") else "ok" for i in judged]
    pb = ["err" if p[i] in ("minor", "major") else "ok" for i in judged]
    rm = ["maj" if r[i] == "major" else "no" for i in judged]
    pm = ["maj" if p[i] == "major" else "no" for i in judged]
    tp = sum(x == y == "maj" for x, y in zip(rm, pm))
    return {"n": len(ds), "exact": round(sum(x == y for x, y in zip(r, p)) / len(ds), 3) if ds else None,
            "kappa4": kappa(r, p, V), "kappa_error": kappa(rb, pb, ("err", "ok")), "kappa_major": kappa(rm, pm, ("maj", "no")),
            "major_recall": round(tp / rm.count("maj"), 3) if rm.count("maj") else None,
            "major_precision": round(tp / pm.count("maj"), 3) if pm.count("maj") else None,
            "pred_major_rate": round(pm.count("maj") / len(judged), 3) if judged else None,
            "pred_error_rate": round(pb.count("err") / len(judged), 3) if judged else None,
            "pred_cannot_tell": p.count("cannot_tell")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_glob"); ap.add_argument("judged")
    ap.add_argument("--panels", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    ref = {}
    for f in sorted(glob.glob(a.ref_glob)):
        for l in open(f):
            j = json.loads(l); ref[j["draw"]] = j["verdict"]
    preds = {}
    for f in glob.glob(os.path.join(a.judged, "*.jsonl")):
        for l in open(f):
            j = json.loads(l)
            if j.get("parsed"): preds.setdefault(j["model"], {})[j["draw"]] = j["parsed"]["verdict"]
    out = {"reference": {"n": len(ref), "verdicts": dict(collections.Counter(ref.values()))}, "models": {}, "panels": {}}
    for m, p in sorted(preds.items()):
        out["models"][m.split("/")[-1]] = scores(ref, p)
    panels = [x.split(",") for x in a.panels.split(";") if x] if a.panels else []
    if not panels:  # every 3-model combination
        names = sorted(preds)
        panels = [list(c) for c in itertools.combinations(names, 3)]
    for pan in panels:
        full = [m if m in preds else next((k for k in preds if k.endswith(m)), m) for m in pan]
        if not all(m in preds for m in full): continue
        common = set.intersection(*(set(preds[m]) for m in full))
        maj = {}
        for d in common:
            c = collections.Counter(preds[m][d] for m in full).most_common(1)[0]
            maj[d] = c[0] if c[1] >= 2 else "cannot_tell"
        out["panels"]["+".join(m.split("/")[-1] for m in full)] = scores(ref, maj)
    best = sorted(out["panels"].items(), key=lambda kv: -((kv[1]["kappa_error"] or 0) + (kv[1]["kappa_major"] or 0)))[:8]
    out["best_panels"] = [k for k, _ in best]
    if a.out: json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out["reference"]))
    for m, s in out["models"].items(): print("MODEL", m, json.dumps(s))
    for k in out["best_panels"]: print("PANEL", k, json.dumps(out["panels"][k]))


if __name__ == "__main__":
    main()
