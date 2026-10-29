#!/usr/bin/env python3
"""Second source for Gate 15: the pub-date elements and article history in the PMC XML. Usage: pmc_dates.py PMC... """
import sys, time, urllib.request, xml.etree.ElementTree as ET
ids = [p.replace("PMC", "") for p in sys.argv[1:]]
for i in range(0, len(ids), 20):
    x = ET.fromstring(urllib.request.urlopen("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=" + ",".join(ids[i:i+20]), timeout=120).read())
    for a in x.iter("article"):
        meta = a.find("front/article-meta")
        pmc = [e.text for e in meta.findall("article-id") if e.get("pub-id-type") in ("pmc", "pmcid", "pmcaid")]
        ds = []
        for d in meta.findall("pub-date"):
            ds.append(f'{d.get("pub-type") or d.get("date-type")}={d.findtext("year")}-{d.findtext("month") or "?"}-{d.findtext("day") or "?"}')
        for d in meta.findall("history/date"):
            ds.append(f'{d.get("date-type")}={d.findtext("year")}-{d.findtext("month") or "?"}-{d.findtext("day") or "?"}')
        print(pmc, "; ".join(ds))
    time.sleep(0.5)
