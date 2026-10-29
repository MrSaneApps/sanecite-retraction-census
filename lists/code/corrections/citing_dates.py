#!/usr/bin/env python3
"""Europe PMC first-publication dates for every citing paper of the given retracted works (all rows in
citations.csv, not only in-scope ones). Usage: citing_dates.py PMID [PMID ...]. Merges into citing_fpd.json."""
import csv, json, os, sys, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.expanduser("site/data/phase2")
want = set(sys.argv[1:])
rows = [r for r in csv.DictReader(open(f"{P2}/citations.csv")) if r["retracted_pmid"] in want]
path = f"{HERE}/citing_fpd.json"
out = json.load(open(path)) if os.path.exists(path) else {}
pmcs = sorted({r["citing_pmcid"] for r in rows} - set(out))
for i in range(0, len(pmcs), 50):
    q = " OR ".join(f"PMCID:{p}" for p in pmcs[i:i + 50])
    for t in range(3):
        try:
            x = json.loads(urllib.request.urlopen("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
                {"query": q, "format": "json", "pageSize": 1000, "resultType": "core"}), timeout=90).read()); break
        except Exception:
            x = None; time.sleep(3 * (t + 1))
    for r in (x or {}).get("resultList", {}).get("result", []):
        if r.get("pmcid"):
            out[r["pmcid"]] = {"fpd": r.get("firstPublicationDate"), "epub": r.get("electronicPublicationDate"), "py": r.get("pubYear")}
    time.sleep(0.5)
json.dump(out, open(path, "w"), indent=0, sort_keys=True)
for r in sorted(rows, key=lambda r: (r["retracted_pmid"], r["citing_year"])):
    d = out.get(r["citing_pmcid"], {})
    print(r["retracted_pmid"], r["retraction_year"], r["citing_pmcid"], r["citing_year"], d.get("fpd"), d.get("epub"), r["citing_journal"], r["label"], r["retraction_reason"])
