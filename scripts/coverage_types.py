#!/usr/bin/env python3
"""Planned analyses 4 and 5 (PROTOCOL.md), run after analyze_census.py.
4. Open-access coverage: compare read vs unread later citers (citing year, publication type, retraction reason, field)
   and re-weight the primary rate (a) so each retracted paper counts by ALL its later citations, (b) by citing year.
5. Where reliance lands: substantive and aware rates by citing-paper type (Europe PMC publication types).
Inputs: census_rows.jsonl, citer_meta.jsonl, stage1_papers.jsonl. Output: coverage_types.json
usage: SANECITE_DATA=... coverage_types.py"""
import collections, json, os, random, re
DATA = os.environ["SANECITE_DATA"]
ADMIN_G = "administrative (no fault found in the science)"

def ptype(s):
    s = (s or "").lower()
    if re.search(r"guideline", s): return "guideline"
    if "meta-analysis" in s: return "meta-analysis"
    if re.search(r"systematic[- ]review", s): return "systematic review"
    if "review" in s: return "review"
    if re.search(r"randomi[sz]ed controlled trial|clinical trial", s): return "clinical trial"
    if "case report" in s or "case-report" in s: return "case report"
    if re.search(r"letter|editorial|comment", s): return "letter, editorial or comment"
    if "research-article" in s or "journal article" in s: return "research article"
    return "other"
def ybin(y):
    y = int(y) if str(y or "").isdigit() else None
    if y is None: return "?"
    return "<=2010" if y <= 2010 else "2011-2015" if y <= 2015 else "2016-2019" if y <= 2019 else "2020-2022" if y <= 2022 else "2023-2026"

rows = [json.loads(l) for l in open(f"{DATA}/census_rows.jsonl")]
meta = {}
for l in open(f"{DATA}/citer_meta.jsonl"):
    m = json.loads(l); meta[m["pmid"]] = m
papers = {json.loads(l)["pmid"]: json.loads(l) for l in open(f"{DATA}/stage1_papers.jsonl")}
read = {(r["paper"], r["pair_id"].split(">")[1]) for r in rows}
reason_of = {r["paper"]: r["reason"] for r in rows}
field_of = {r["paper"]: r["field"] for r in rows}
type_of = {}
for pm, m in meta.items():
    for c in m["citers"]:
        if c.get("pmcid"): type_of[(pm, c["pmcid"])] = ptype(c.get("type"))

# 4a. read vs unread citers
comp = {k: {"read": collections.Counter(), "unread": collections.Counter()} for k in ("citing_year", "type")}
tot = collections.Counter()
for pm, m in meta.items():
    for c in m["citers"]:
        g = "read" if (pm, c.get("pmcid")) in read else "unread"
        tot[g] += 1
        comp["citing_year"][g][ybin(c.get("year"))] += 1
        comp["type"][g][ptype(c.get("type"))] += 1
# retraction reason group and field, for every retracted paper (read or not); shared rules in groups.py
from groups import reason_group, field_group
for pm, p in papers.items():
    reason_of.setdefault(pm, reason_group(p.get("reason"))); field_of.setdefault(pm, field_group(p.get("subject")))
comp["reason"] = {"read": collections.Counter(), "unread": collections.Counter()}
comp["field"] = {"read": collections.Counter(), "unread": collections.Counter()}
for pm, m in meta.items():
    for c in m["citers"]:
        g = "read" if (pm, c.get("pmcid")) in read else "unread"
        comp["reason"][g][reason_of.get(pm, "?")] += 1
        comp["field"][g][field_of.get(pm, "?")] += 1

def shares(cn): n = sum(cn.values()); return {k: round(v / n, 4) for k, v in sorted(cn.items())} if n else {}
out = {"citers_total": sum(tot.values()), "citers_read": tot["read"], "citers_unread": tot["unread"],
       "read_vs_unread": {k: {g: shares(v[g]) for g in v} for k, v in comp.items()}}

# 4b. re-weighted primary rate (non-administrative, judged)
judged = [r for r in rows if r["label"] != "unclear" and r["reason"] != ADMIN_G]
by_paper = collections.defaultdict(list)
for r in judged: by_paper[r["paper"]].append(r)
all_cites = {pm: m["n"] for pm, m in meta.items()}
yr_all, yr_read = collections.Counter(), collections.Counter()
for pm, m in meta.items():
    if reason_of.get(pm, "") == ADMIN_G: continue
    for c in m["citers"]: yr_all[ybin(c.get("year"))] += 1
for r in judged: yr_read[ybin(r.get("citing_year"))] += 1
def rates(sample_papers):
    rs = [r for p in sample_papers for r in by_paper[p]]
    if not rs: return None
    raw = sum(r["label"] == "substantive" for r in rs) / len(rs)
    w = {p: all_cites.get(p, len(by_paper[p])) / len(by_paper[p]) for p in set(sample_papers)}
    pw = sum(w[r["paper"]] * (r["label"] == "substantive") for r in rs) / sum(w[r["paper"]] for r in rs)
    yr_n = collections.Counter(ybin(r.get("citing_year")) for r in rs)
    A = sum(yr_all[b] for b in yr_n)
    yw = sum((yr_all[ybin(r.get("citing_year"))] / A) / yr_n[ybin(r.get("citing_year"))] * (r["label"] == "substantive") for r in rs)
    return raw, pw, yw
ps = list(by_paper)
point = rates(ps); rnd = random.Random(7); boots = []
for _ in range(200): boots.append(rates([rnd.choice(ps) for _ in ps]))
def ci(i): v = sorted(b[i] for b in boots if b); return [round(v[5], 4), round(v[194], 4)]
out["primary_reweighted"] = {"raw": {"rate": round(point[0], 4), "ci95": ci(0)},
                             "weighted_by_all_later_citations_per_paper": {"rate": round(point[1], 4), "ci95": ci(1)},
                             "weighted_by_citing_year": {"rate": round(point[2], 4), "ci95": ci(2)},
                             "n_pairs": len(judged), "n_papers": len(ps)}

# 5. by citing-paper type
bt = collections.defaultdict(collections.Counter)
for r in judged:
    t = type_of.get((r["paper"], r["pair_id"].split(">")[1]), "unknown")
    bt[t]["n"] += 1; bt[t][r["label"]] += 1
out["by_citing_type"] = {t: {"n": c["n"], "substantive": c["substantive"], "aware": c["aware"],
                             "substantive_rate": round(c["substantive"] / c["n"], 4), "aware_rate": round(c["aware"] / c["n"], 4)}
                         for t, c in sorted(bt.items(), key=lambda x: -x[1]["n"])}
json.dump(out, open(f"{DATA}/coverage_types.json", "w"), indent=1)
print(json.dumps(out, indent=1))
