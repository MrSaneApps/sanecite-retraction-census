#!/usr/bin/env python3
"""Gate 1: PubMed and Crossref dates for given notice PMIDs. Usage: notice_dates.py NOTICE_PMID ..."""
import json, sys, time, urllib.request, xml.etree.ElementTree as ET
def get(u, raw=False):
    b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SaneCite/1.0 (mailto:hi@saneapps.com)"}), timeout=90).read()
    return b if raw else json.loads(b)
y = ET.fromstring(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=" + ",".join(sys.argv[1:]), raw=True))
for a in y.iter("PubmedArticle"):
    pm = a.find(".//MedlineCitation/PMID").text
    ad = a.find(".//Article/ArticleDate")
    pd = a.find(".//JournalIssue/PubDate")
    hist = {d.get("PubStatus"): "-".join(filter(None, (d.findtext("Year"), d.findtext("Month"), d.findtext("Day")))) for d in a.iter("PubMedPubDate")}
    doi = ([e.text for e in a.iter("ELocationID") if e.get("EIdType") == "doi"] + [e.text for e in a.iter("ArticleId") if e.get("IdType") == "doi"] + [""])[0].lower()
    rof = [c.findtext("PMID") for c in a.iter("CommentsCorrections") if c.get("RefType") == "RetractionOf"]
    cr = {}
    if doi:
        try:
            m = get("https://api.crossref.org/works/" + doi)["message"]
            dp = lambda k: "-".join(str(v) for v in (m.get(k) or {}).get("date-parts", [[]])[0])
            cr = {"online": dp("published-online"), "print": dp("published-print"), "created": dp("created"), "issued": dp("issued")}
        except Exception as e:
            cr = {"err": str(e)[:60]}
        time.sleep(0.3)
    abst = " ".join(t.text or "" for t in a.iter("AbstractText"))
    print(json.dumps({"notice": pm, "retraction_of": rof, "article_date": "-".join(ad.findtext(k) for k in ("Year", "Month", "Day")) if ad is not None else "",
                      "pubdate": " ".join(filter(None, (pd.findtext(k) for k in ("Year", "Month", "Day", "MedlineDate")))) if pd is not None else "",
                      "pubmed_history": hist, "doi": doi, "crossref": cr, "title": a.findtext(".//ArticleTitle"), "abstract": abst[:600]}, ensure_ascii=False))
