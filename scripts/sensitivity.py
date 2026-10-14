#!/usr/bin/env python3
"""Robustness analyses (PROTOCOL.md amendment 2), run after analyze_census.py.
Primary outcome (substantive share of judged, non-administrative pairs) under:
  S1 citing papers that are themselves retracted removed; S2 citations >= 2 years after retraction;
  S3 only pairs whose every passage the three models labelled unanimously; S4 first passage only;
  S5 pairs matched by PubMed ID or DOI only (title matches removed).
Plus: inter-model agreement (Fleiss kappa, passage level) and self-citation (exploratory: shared author surname and
first initial between the retracted and the citing paper).  Output: sensitivity.json
usage: SANECITE_DATA=... sensitivity.py <retraction_watch.csv>"""
import collections, csv, gzip, json, os, random, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__)); import panel as P, classify as C
DATA, RW = os.environ["SANECITE_DATA"], sys.argv[1]
ADMIN_G = "administrative (no fault found in the science)"
XML = os.environ.get("SANECITE_XML_CACHE", f"{DATA}/xml")
RANK = {"aware": 3, "substantive": 2, "perfunctory": 1, "unclear": 0}

def norm(s): return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()

rows = {json.loads(l)["pair_id"]: json.loads(l) for l in open(f"{DATA}/census_rows.jsonl")}
s2 = {}
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: r = json.loads(l)
    except Exception: continue
    if r["pair_id"] in rows: s2[r["pair_id"]] = r
L = collections.defaultdict(dict)
for tag in ("jev", "clef", "gemma"):
    for l in open(f"{DATA}/stage3_{tag}.jsonl"):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("label") and r["pair_id"] in rows: L[(r["pair_id"], r["ctx"])][r["model"]] = r

rw_pmids, rw_auth = set(), {}
for x in csv.DictReader(open(RW, encoding="utf-8", errors="replace")):
    p = (x["OriginalPaperPubMedID"] or "").strip()
    if p and p != "0" and x["RetractionNature"] == "Retraction": rw_pmids.add(p)
    if p: rw_auth[p] = x["Author"]
citer_pmid = {}
for l in open(f"{DATA}/citer_meta.jsonl"):
    m = json.loads(l)
    for c in m["citers"]:
        if c.get("pmcid") and c.get("src") == "MED": citer_pmid[(m["pmid"], c["pmcid"])] = c["id"]

judged = [r for r in rows.values() if r["label"] != "unclear" and r["reason"] != ADMIN_G]
def stat(rs, lab="substantive", B=200):
    rs = [r for r in rs if r.get("_lab", r["label"]) != "unclear"]
    if not rs: return None
    f = lambda r: r.get("_lab", r["label"]) == lab
    by = collections.defaultdict(list)
    for r in rs: by[r["paper"]].append(f(r))
    keys, rnd, v = list(by), random.Random(3), []
    sums = {k: (sum(x), len(x)) for k, x in by.items()}
    for _ in range(B):
        a = b = 0
        for k in (rnd.choice(keys) for _ in keys): a += sums[k][0]; b += sums[k][1]
        v.append(a / max(1, b))
    v.sort()
    return {"rate": round(sum(map(f, rs)) / len(rs), 4), "ci95": [round(v[5], 4), round(v[194], 4)], "n": len(rs)}

out = {"primary": stat(judged)}
retracted_citer = lambda r: citer_pmid.get((r["paper"], r["pair_id"].split(">")[1])) in rw_pmids
out["S1_citing_paper_not_retracted"] = stat([r for r in judged if not retracted_citer(r)])
out["S1_citing_papers_retracted_n"] = sum(retracted_citer(r) for r in judged)
out["S2_two_or_more_years_after"] = stat([r for r in judged if (r.get("years_after") or 0) >= 2])
out["S3_all_passages_unanimous"] = stat([r for r in judged if r["route"] == "unanimous"])
first = []
for r in judged:
    rec = s2.get(r["pair_id"])
    if not rec: continue
    lab, _ = P.combine(L.get((r["pair_id"], 0), {}), " ".join(C.passage(rec, 0)))
    if lab: first.append(dict(r, _lab=lab))
out["S4_first_passage_only"] = stat(first)
out["S5_id_matched_only"] = stat([r for r in judged if s2.get(r["pair_id"], {}).get("match") in ("pmid", "doi")])

# Fleiss kappa over passages with all three labels (label and stance)
def fleiss(items, cats):
    N = len(items); n = 3
    if not N: return None
    p = {c: sum(it.count(c) for it in items) / (N * n) for c in cats}
    Pi = [(sum(it.count(c) ** 2 for c in cats) - n) / (n * (n - 1)) for it in items]
    Pb, Pe = sum(Pi) / N, sum(v * v for v in p.values())
    return round((Pb - Pe) / (1 - Pe), 4) if Pe < 1 else None
labs, stances = [], []
for (pid, i), d in L.items():
    if all(m in d for m in P.PANEL):
        labs.append([d[m]["label"] for m in P.PANEL]); stances.append([d[m].get("stance") for m in P.PANEL])
out["fleiss_kappa"] = {"label": fleiss(labs, ["aware", "substantive", "perfunctory", "unclear"]),
                       "stance": fleiss(stances, ["disputed", "neutral"]), "passages": len(labs)}

# Self-citation (exploratory)
def rw_keys(s):
    ks = set()
    for a in (s or "").split(";"):
        parts = norm(a).replace(".", " ").split()
        if len(parts) >= 2: ks.add((parts[-1], parts[0][0]))
    return ks
def xml_keys(pmcid):
    fn = f"{XML}/{pmcid}.xml.gz"
    if not os.path.exists(fn): return None
    try: t = gzip.open(fn, "rt", encoding="utf-8", errors="replace").read()
    except Exception: return None
    ks = set()
    for m in re.finditer(r'<contrib contrib-type="author".*?</contrib>', t, re.S):
        sn = re.search(r"<surname>(.*?)</surname>", m.group(0)); gn = re.search(r"<given-names[^>]*>(.*?)</given-names>", m.group(0))
        if sn and gn and norm(gn.group(1)): ks.add((norm(sn.group(1)).split()[-1] if norm(sn.group(1)) else "", norm(gn.group(1))[0]))
    return ks
selfc = collections.Counter(); self_rows, other_rows = [], []
for r in judged:
    ck = xml_keys(r["pair_id"].split(">")[1]); rk = rw_keys(rw_auth.get(r["paper"]))
    if ck is None or not rk: selfc["unknown"] += 1; continue
    (self_rows if ck & rk else other_rows).append(r)
out["self_citation_exploratory"] = {"self": len(self_rows), "not_self": len(other_rows), "unknown": selfc["unknown"],
                                    "substantive_self": stat(self_rows), "substantive_not_self": stat(other_rows),
                                    "aware_self": stat(self_rows, "aware"), "aware_not_self": stat(other_rows, "aware")}
json.dump(out, open(f"{DATA}/sensitivity.json", "w"), indent=1)
print(json.dumps(out, indent=1))
