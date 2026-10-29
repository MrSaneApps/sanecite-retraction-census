import json, glob, sys
def load_gold(b):
    if b == "b5":
        g = {}
        for f in sorted(glob.glob(f"{b}/ref/ref-*.jsonl")):
            for l in open(f):
                r = json.loads(l); g[r["draw"]] = r["verdict"]
        return g
    return {json.loads(l)["draw"]: json.loads(l)["verdict"] for l in open(f"{b}/gold/gold.jsonl")}
def load_clef(b):
    c = {}
    for l in open(f"{b}/bake_clef/clef.jsonl"):
        r = json.loads(l); p = (r.get("parsed") or {}).get("probabilities")
        if p: c[r["draw"]] = p
    return c
def auc(P, N):
    return sum((p > n) + 0.5 * (p == n) for p in P for n in N) / (len(P) * len(N))
def report(label, rows):
    rows = [(p, g) for p, g in rows if g != "cannot_tell"]
    maj = [p["major"] for p, g in rows if g == "major"]; non = [p["major"] for p, g in rows if g != "major"]
    err = [p["major"] + p["minor"] for p, g in rows if g in ("major", "minor")]
    ok = [p["major"] + p["minor"] for p, g in rows if g == "accurate"]
    print(f"{label}: n={len(rows)} majors={len(maj)} AUC major={auc(maj, non):.3f} AUC any error={auc(err, ok):.3f}")
    for t in (0.10, 0.12):
        fl = [g for p, g in rows if p["major"] >= t]
        print(f"  P(major)>={t:.2f}: caught {sum(g=='major' for g in fl)}/{len(maj)} "
              f"({sum(g=='major' for g in fl)/max(1,len(maj)):.0%}), flagged {len(fl)}/{len(rows)} ({len(fl)/len(rows):.0%})")
allrows = {}
for b in ("b3", "b4", "b5"):
    try:
        g, c = load_gold(b), load_clef(b)
    except FileNotFoundError as e:
        print(b, "missing", e); continue
    allrows[b] = [(c[d], g[d]) for d in c if d in g]
    print(f"{b}: clef {len(c)} answers, matched {len(allrows[b])}")
if "b3" in allrows and "b4" in allrows:
    report("TEST b3+b4 (pre-registered)", allrows["b3"] + allrows["b4"])
for b in allrows: report(b, allrows[b])
