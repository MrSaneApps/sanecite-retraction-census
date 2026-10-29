#!/usr/bin/env python3
"""Author lists (with ORCID where Europe PMC has one) for every citing paper that cites a retracted paper as
support, from the public Europe PMC REST API. Resumable: skips PMCIDs already in the output. One request at a time.
usage: python3 fetch_authors.py <citations.csv> <out.jsonl>"""
import csv, json, os, sys, time, urllib.parse, urllib.request

src, out = sys.argv[1], sys.argv[2]
ADMIN = "administrative (no fault found in the science)"
want = sorted({r["citing_pmcid"] for r in csv.DictReader(open(src))
               if r["label"] == "substantive" and r["retraction_reason"] != ADMIN})
have = set()
if os.path.exists(out):
    for line in open(out):
        have.add(json.loads(line)["pmcid"])
todo = [p for p in want if p not in have]
print(time.strftime("%H:%M:%S"), f"want {len(want)} have {len(have)} todo {len(todo)}", flush=True)
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
with open(out, "a") as f:
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        q = " OR ".join(f"PMCID:{p}" for p in batch)
        url = API + "?" + urllib.parse.urlencode({"query": q, "resultType": "core", "format": "json", "pageSize": 1000})
        for attempt in range(3):
            try:
                d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SaneCite research (hi@saneapps.com)"}), timeout=60))
                break
            except Exception as e:
                print(time.strftime("%H:%M:%S"), "retry", attempt + 1, type(e).__name__, flush=True); time.sleep(5 * (attempt + 1))
        else:
            print(time.strftime("%H:%M:%S"), "FAIL batch", i, flush=True); continue
        got = 0
        for r in d.get("resultList", {}).get("result", []):
            if r.get("pmcid") not in batch: continue
            auth = [{"name": a.get("fullName"), "first": a.get("firstName"), "last": a.get("lastName"),
                     "orcid": (a.get("authorId") or {}).get("value") if (a.get("authorId") or {}).get("type") == "ORCID" else None,
                     "aff": [x.get("affiliation") for x in (a.get("authorAffiliationDetailsList") or {}).get("authorAffiliation", [])][:2]}
                    for a in (r.get("authorList") or {}).get("author", [])]
            f.write(json.dumps({"pmcid": r["pmcid"], "title": r.get("title"), "journal": (r.get("journalInfo") or {}).get("journal", {}).get("title"),
                                "year": r.get("pubYear"), "authors": auth}) + "\n"); got += 1
        f.flush()
        print(time.strftime("%H:%M:%S"), f"batch {i // 100 + 1}/{(len(todo) + 99) // 100} got {got}/{len(batch)}", flush=True)
        time.sleep(1)
print(time.strftime("%H:%M:%S"), "DONE", flush=True)
