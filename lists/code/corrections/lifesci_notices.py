#!/usr/bin/env python3
"""Gate 1 check for every Life Sci retracted work in the Lists data: PubMed RetractionIn link on the article,
the notice's PubMed dates (electronic ArticleDate and PubDate), the notice DOI and its Crossref online date.
Writes lifesci_notices.json beside this file. Read-only public APIs."""
import csv, json, os, time, urllib.request, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.expanduser("site/data/phase2")
def get(u, raw=False):
    for i in range(3):
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SaneCite/1.0 (mailto:hi@saneapps.com)"}), timeout=90).read()
            return b if raw else json.loads(b)
        except Exception:
            time.sleep(3 * (i + 1))
    return None
papers = [x for x in json.load(open(f"{P2}/papers.json"))["papers"] if x[2] in ("Life Sci", "Life Sciences")]
ry = defaultdict(Counter)
for r in csv.DictReader(open(f"{P2}/citations.csv")):
    ry[r["retracted_pmid"]][r["retraction_year"]] += 1
ids = [x[0] for x in papers]
x = ET.fromstring(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=" + ",".join(ids), raw=True))
art = {}
for a in x.iter("PubmedArticle"):
    pm = a.find(".//MedlineCitation/PMID").text
    rin = [c.find("PMID").text for c in a.iter("CommentsCorrections") if c.get("RefType") == "RetractionIn" and c.find("PMID") is not None]
    art[pm] = rin
notice_ids = sorted({n for v in art.values() for n in v})
time.sleep(1)
y = ET.fromstring(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=" + ",".join(notice_ids), raw=True))
notes = {}
for a in y.iter("PubmedArticle"):
    pm = a.find(".//MedlineCitation/PMID").text
    ad = a.find(".//Article/ArticleDate")
    pd = a.find(".//JournalIssue/PubDate")
    doi = [e.text for e in a.iter("ELocationID") if e.get("EIdType") == "doi"] + [e.text for e in a.iter("ArticleId") if e.get("IdType") == "doi"]
    vol = a.findtext(".//JournalIssue/Volume")
    notes[pm] = {"article_date": "-".join(ad.findtext(k) for k in ("Year", "Month", "Day")) if ad is not None else "",
                 "pubdate": " ".join(filter(None, (pd.findtext(k) for k in ("Year", "Month", "Day", "MedlineDate")))) if pd is not None else "",
                 "volume": vol, "doi": doi[0].lower() if doi else "", "title": a.findtext(".//ArticleTitle")}
for pm, n in notes.items():
    if n["doi"]:
        c = get("https://api.crossref.org/works/" + n["doi"])
        m = (c or {}).get("message", {})
        dp = lambda k: "-".join(str(v) for v in (m.get(k) or {}).get("date-parts", [[]])[0])
        n["crossref_online"], n["crossref_print"], n["crossref_created"] = dp("published-online"), dp("published-print"), dp("created")
        time.sleep(0.3)
out = {}
for p in papers:
    out[p[0]] = {"title": p[1], "census_year": dict(ry[p[0]]), "retraction_in": art.get(p[0], []),
                 "notices": {n: notes.get(n) for n in art.get(p[0], [])}}
json.dump(out, open(f"{HERE}/lifesci_notices.json", "w"), indent=1, ensure_ascii=False)
for k, v in sorted(out.items()):
    for n, d in v["notices"].items():
        print(k, v["census_year"], n, d and d["article_date"], d and d["pubdate"], d and d.get("crossref_online"), d and d["doi"])
    if not v["notices"]:
        print(k, v["census_year"], "NO RetractionIn")
