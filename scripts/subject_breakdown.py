#!/usr/bin/env python3
"""Post-hoc breakdown (20 Oct 2026, not in the registered protocol): the headline rates by Retraction Watch subject.
The registered field grouping (groups.field_group, amendment 3) sorts each retracted paper by its whole set of subject
codes: basic life sciences only, health sciences only, both, or "other fields", which is any paper carrying a code
outside those two (often alongside them). Its pattern, \\((\\w+)\\), also skips the "B/T" code, so the 82 citations to
papers coded only B/T fall into "?". This script counts each citation under every top-level subject its retracted
paper carries (a paper with two subjects counts in both), with the census's own cluster bootstrap (analyze_census.boot:
400 draws over retracted papers, seed 1). Reads the public data files.
usage: python3 scripts/subject_breakdown.py   (writes data/subject_breakdown.json and data/paper_subjects.csv)"""
import collections, csv, gzip, json, os, random, re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
ADMIN = "administrative (no fault found in the science)"
NAMES = {"BLS": "Basic life sciences", "HSC": "Health sciences", "PHY": "Physical sciences", "SOC": "Social sciences",
         "B/T": "Business and technology", "ENV": "Environment", "HUM": "Humanities"}
CODE = re.compile(r"\(([A-Z]+(?:/[A-Z]+)?)\)")


def lines(name):
    with gzip.open(os.path.join(DATA, name), "rt", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def boot(rs, pred, B=400, seed=1):  # copied from analyze_census.py
    by = collections.defaultdict(list)
    for r in rs: by[r["paper"]].append(pred(r))
    keys = list(by); rnd = random.Random(seed); vals = []
    sums = {k: (sum(v), len(v)) for k, v in by.items()}
    for _ in range(B):
        a = b = 0
        for k in (rnd.choice(keys) for _ in keys): a += sums[k][0]; b += sums[k][1]
        vals.append(a / max(1, b))
    vals.sort(); return [round(vals[int(.025 * B)], 6), round(vals[int(.975 * B) - 1], 6)]


def stat(rs, pred):
    k = sum(map(pred, rs))
    return {"rate": round(k / len(rs), 4), "k": k, "ci95": boot(rs, pred), "n": len(rs), "papers": len({r["paper"] for r in rs})}


subject = {p["pmid"]: p.get("subject") or "" for p in lines("stage1_papers.jsonl.gz")}
judged = [r for r in lines("census_rows.jsonl.gz") if r["label"] != "unclear" and r["reason"] != ADMIN]
codes = {r["paper"]: sorted(set(CODE.findall(subject.get(r["paper"], "")))) for r in judged}
out = {"note": "Post-hoc, 20 Oct 2026, not in the registered protocol. Judged headline citations by Retraction Watch "
               "top-level subject of the retracted paper; a paper with several subjects counts under each, so groups overlap.",
       "judged": len(judged), "no_subject": sum(not codes[r["paper"]] for r in judged), "subjects": {}}
for c, name in NAMES.items():
    rs = [r for r in judged if c in codes[r["paper"]]]
    out["subjects"][c] = {"name": name, **{lab: stat(rs, lambda r, lab=lab: r["label"] == lab)
                                           for lab in ("substantive", "aware", "perfunctory")}}
json.dump(out, open(os.path.join(DATA, "subject_breakdown.json"), "w"), indent=1)
with open(os.path.join(DATA, "paper_subjects.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["retracted_pmid", "subjects"])
    for p in sorted(codes, key=int): w.writerow([p, ";".join(codes[p])])
for c, s in out["subjects"].items():
    print(f'{c:4} n={s["substantive"]["n"]:6} support={100 * s["substantive"]["k"] / s["substantive"]["n"]:.1f}% '
          f'{s["substantive"]["ci95"]} flagged={100 * s["aware"]["k"] / s["aware"]["n"]:.1f}%')
