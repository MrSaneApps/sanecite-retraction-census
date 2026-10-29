#!/usr/bin/env python3
"""The three named lists for the SaneCite Lists page, from the census and the second reading.
Writes, into <site data/phase2>:
  lists.json             the listed papers, journals and authors, with their census counts and reading results
  list_checks.csv        every citation the second reading looked at, with its verdict and a one-line note
  retraction_status.csv  each retracted paper's PubMed retraction link status (status_all.py)
Rules (owner, 2026-10-20): named lists use only papers PubMed links to a retraction notice; every named entry's
citations are read again before it is listed; ties at the cut are all listed (competition ranking: 1, 2, 2, 4).
  papers   ranked by citations labelled "cited it as support"; entries the reading shows are not support for a
           finding are left off, with the reason shown.
  journals ranked by support count, and by support rate among journals with at least 100 judged citations.
  authors  ORCID only; ranked by citing papers with at least one support citation the reading confirmed. Every
           author whose census count could reach the cut was read (asserted below).
usage: python3 lists_data.py <top10 dir> <site data/phase2 dir>"""
import csv, json, re, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

T, P2 = sys.argv[1], sys.argv[2]
csv.field_size_limit(10 ** 9)
ADMIN = "administrative (no fault found in the science)"
CUT = 10
rank = json.load(open(f"{T}/rank.json"))
status = json.load(open(f"{T}/paper_status_class.json"))
notice = {}
for line in open(f"{T}/paper_status_all.jsonl"):
    d = json.loads(line)
    ids = [c["id"] for c in d.get("cc", []) if c.get("type") == "Retraction in" and c.get("id")]
    if ids: notice[d["pmid"]] = ids[0]
V = {}  # pair_id + group -> verdict row; a pair can sit in more than one list
for kind in ("papers", "journals", "authors"):
    for f in (f"verdicts_{kind}.jsonl", f"verdicts2_{kind}.jsonl"):
        try:
            for line in open(f"{T}/{f}"):
                d = json.loads(line); d["list"] = kind; V[(kind, d["group"], d["pair_id"])] = d
        except FileNotFoundError:
            pass
rows = [r for r in csv.DictReader(open(f"{P2}/citations.csv")) if r["label"] != "unclear" and r["retraction_reason"] != ADMIN
        and status.get(r["retracted_pmid"]) == "retracted (linked)"]
by_pair = {r["pair_id"]: r for r in rows}


def checked(kind, group):
    vs = [v for (k, g, _), v in V.items() if k == kind and g == group]
    return {"read": len(vs), "confirmed": sum(v["verdict"] == "CONFIRM" for v in vs)}


def epmc(query_ids, field):
    """Europe PMC core records for a list of ids (PMCID or EXT_ID), 100 per request, one request at a time."""
    out = {}
    ids = sorted(set(query_ids))
    for i in range(0, len(ids), 100):
        q = " OR ".join(f"{field}:{x}" for x in ids[i:i + 100])
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
            {"query": q, "resultType": "core", "format": "json", "pageSize": 1000})
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SaneCite research (hi@saneapps.com)"}), timeout=60))
        for r in d["resultList"]["result"]:
            out[r.get("pmcid") if field == "PMCID" else r.get("id")] = r
        time.sleep(1)
    return out


def ranked(items, key):
    """Competition ranking, cut at CUT: every entry tied with the 10th is kept."""
    items = sorted(items, key=lambda x: -key(x))
    out = []
    for i, x in enumerate(items):
        x["rank"] = out[-1]["rank"] if out and key(x) == key(out[-1]) else i + 1
        if x["rank"] > CUT: break
        out.append(x)
    return out


# ------------------------------------------------------------------ papers
DROP = {  # left off after reading: what the citations actually use the paper for
    "12609035": "Citations use the p19 lab tool the paper describes, which still works (14 of 15 read). It was retracted over duplicated figures.",
    "21772732": "Citations name a standard randomization method the paper describes; none rests on a result of its own.",
    "32286091": "Retracted for repeating an earlier paper by the same authors on the same survey. That paper is still published "
                "(Psychiatry Res 2020;288:112954), so citations point to findings that remain in the record.",
    "24711954": "A review: citations use its summary figures, which come from other published sources.",
    "35480139": "A review: citations use its summary figures, which come from other published sources.",
}
NOTE = {"18453793": "Most citations use the MMAS-8 adherence questionnaire and its cut-offs. The journal retracted the "
                    "paper after an independent statistical review found its results \"misleading due to issues regarding the "
                    "sensitivity and specificity\" of the scale (notice doi:10.1111/jch.14718)."}
papers = [dict(p) for p in rank["papers"]]
for p in papers:
    p.update(checked("papers", p["pmid"]))
listed = ranked([p for p in papers if p["pmid"] not in DROP], lambda p: p["support"])
dropped = [p for p in papers if p["pmid"] in DROP and p["support"] >= listed[-1]["support"]]
for p in listed + dropped:
    assert p["read"] >= 15, ("paper listed or dropped without its reading", p["pmid"])
    assert p["pmid"] in notice, ("no retraction notice id", p["pmid"])
assert papers[-1]["support"] < listed[-1]["support"], "rank.json papers stop before the cut; widen rank.py"
meta = epmc([p["pmid"] for p in listed + dropped], "EXT_ID")
PAPERS = []
for p in listed + dropped:
    m = meta[p["pmid"]]
    first = (m.get("authorString") or "").split(",")[0].strip()
    PAPERS.append({"rank": p.get("rank"), "pmid": p["pmid"], "title": re.sub(r"^(RETRACTED|Retracted|Retraction)[:.]\s*", "", m.get("title", p["title"])).rstrip("."), "first_author": first,
                   "journal": (m.get("journalInfo") or {}).get("journal", {}).get("isoabbreviation") or p["journal"],
                   "year": min(filter(None, (m.get("pubYear"), (m.get("firstPublicationDate") or "")[:4]))), "doi": m.get("doi"), "retraction_year": p["retraction_year"], "reason": p["reason"],
                   "notice_pmid": notice[p["pmid"]], "support": p["support"], "judged": p["judged"], "flagged": p["flagged"],
                   "read": p["read"], "confirmed": p["confirmed"], "note": NOTE.get(p["pmid"], ""),
                   "left_off": DROP.get(p["pmid"], "")})

# ------------------------------------------------------------------ journals
JOURNALS = {}
for k in ("journals_by_count", "journals_by_rate"):
    key = (lambda j: j["support"]) if k == "journals_by_count" else (lambda j: j["support"] / j["judged"])
    js = ranked([dict(j) for j in rank[k]], key)
    for j in js:
        j.update(checked("journals", j["journal"]))
        assert j["read"] >= 10, ("journal listed without its reading", j["journal"])
        j.pop("rate", None); j.pop("rate_low95", None)
    JOURNALS[k.replace("journals_", "")] = js

# ------------------------------------------------------------------ authors
auth = {}
for line in open(f"{T}/citer_authors.jsonl"):
    d = json.loads(line); auth[d["pmcid"]] = d
groups = {g for (k, g, _) in V if k == "authors"}
A = []
for a in rank["authors"]:
    g = f"{a['orcid']} {a['name']}"
    if g not in groups: continue
    vs = [v for (k, gg, _), v in V.items() if k == "authors" and gg == g]
    conf = [v for v in vs if v["verdict"] == "CONFIRM"]
    full = Counter()
    for pmc in a["papers"]:
        for x in auth[pmc]["authors"]:
            if x.get("orcid") == a["orcid"] and x.get("first") and x.get("last"): full[f"{x['first']} {x['last']}"] += 1
    A.append({"orcid": a["orcid"], "name": full.most_common(1)[0][0] if full else a["name"], "short": a["name"],
              "papers_found": a["papers"], "papers_confirmed": sorted({v["pair_id"].split(">")[1] for v in conf}),
              "citations_read": len(vs), "citations_confirmed": len(conf),
              "retracted_cited": len({v["pair_id"].split(">")[0] for v in conf})})
AUTHORS = ranked(A, lambda a: len(a["papers_confirmed"]))
cut = len(AUTHORS[-1]["papers_confirmed"])
unread = [a for a in rank["authors"] if a["n_papers"] >= cut and f"{a['orcid']} {a['name']}" not in groups]
assert not unread, ("authors who could reach the cut were not read", [a["name"] for a in unread])
assert rank["authors"][-1]["n_papers"] < cut, "rank.json authors stop before the cut; widen rank.py"
pt = epmc([p for a in AUTHORS for p in a["papers_confirmed"]], "PMCID")
review = lambda pmc: any("review" in t.lower() for t in (pt.get(pmc, {}).get("pubTypeList") or {}).get("pubType", []))
for a in AUTHORS:
    a["reviews"] = sum(review(p) for p in a["papers_confirmed"])
    a["pubtype_missing"] = sum(p not in pt for p in a["papers_confirmed"])
    mine = set(a["papers_confirmed"])
    a["shares"] = [{"orcid": b["orcid"], "short": b["short"], "papers": len(mine & set(b["papers_confirmed"]))}
                   for b in AUTHORS if b is not a and len(mine & set(b["papers_confirmed"])) * 2 >= len(mine)]

# ------------------------------------------------------------------ write
with open(f"{P2}/list_checks.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["list", "entry", "pair_id", "retracted_pmid", "citing_pmcid", "census_label", "second_reading", "note"])
    WORD = {"CONFIRM": "cited it as support", "REJECT_PASSING": "mentioned it in passing", "REJECT_AWARE": "flagged it as retracted or unreliable",
            "REJECT_OTHER": "other: wrong reference, or not about the paper"}
    for (k, g, pid), v in sorted(V.items()):
        w.writerow([k[:-1], g, pid, *pid.split(">"), "cited it as support", WORD[v["verdict"]], v["reason"]])
with open(f"{P2}/retraction_status.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["retracted_pmid", "pubmed_status", "retraction_notice_pmid"])
    for pmid in sorted(status, key=int):
        w.writerow([pmid, status[pmid], notice.get(pmid, "")])
json.dump({"made": time.strftime("%Y-%m-%d"), "cut": CUT, "journals_min_n": rank["journals_min_n"],
           "journals_eligible": rank["journals_eligible"], "authors_note": rank["authors_note"],
           "papers": PAPERS, "journals": JOURNALS, "authors": AUTHORS}, open(f"{P2}/lists.json", "w"), indent=1)
print("papers", [(p["rank"], p["pmid"], p["support"]) for p in PAPERS])
for k, js in JOURNALS.items(): print(k, [(j["rank"], j["journal"], j["confirmed"]) for j in js])
print("authors", [(a["rank"], a["short"], len(a["papers_confirmed"]), a["reviews"], a["pubtype_missing"], [s["short"] for s in a["shares"]]) for a in AUTHORS])
