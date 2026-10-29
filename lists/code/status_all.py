#!/usr/bin/env python3
"""PubMed correction links (via Europe PMC) for every retracted PMID in the Phase 2 census. Resumable.
usage: python3 status_all.py <citations.csv> <out.jsonl>"""
import csv, json, os, sys, time, urllib.parse, urllib.request
src, out = sys.argv[1], sys.argv[2]
want = sorted({r["retracted_pmid"] for r in csv.DictReader(open(src))})
have = {json.loads(l)["pmid"] for l in open(out)} if os.path.exists(out) else set()
todo = [p for p in want if p not in have]
print(time.strftime("%H:%M:%S"), f"want {len(want)} todo {len(todo)}", flush=True)
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
with open(out, "a") as f:
    for i in range(0, len(todo), 100):
        b = todo[i:i + 100]
        q = "SRC:MED AND (" + " OR ".join(f"EXT_ID:{p}" for p in b) + ")"
        url = API + "?" + urllib.parse.urlencode({"query": q, "resultType": "core", "format": "json", "pageSize": 1000})
        for a in range(3):
            try:
                d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SaneCite research (hi@saneapps.com)"}), timeout=90)); break
            except Exception as e:
                print(time.strftime("%H:%M:%S"), "retry", a + 1, type(e).__name__, flush=True); time.sleep(5 * (a + 1))
        else:
            print(time.strftime("%H:%M:%S"), "FAIL batch", i, flush=True); continue
        seen = set()
        for r in d.get("resultList", {}).get("result", []):
            p = r.get("pmid")
            if p not in b or p in seen: continue
            seen.add(p)
            cc = [{"type": c.get("type"), "id": c.get("id"), "ref": c.get("reference")} for c in (r.get("commentCorrectionList") or {}).get("commentCorrection", [])]
            f.write(json.dumps({"pmid": p, "doi": r.get("doi"), "title": r.get("title"), "pubtypes": (r.get("pubTypeList") or {}).get("pubType", []), "cc": cc}) + "\n")
        for p in set(b) - seen:
            f.write(json.dumps({"pmid": p, "missing": True}) + "\n")
        f.flush()
        print(time.strftime("%H:%M:%S"), f"batch {i // 100 + 1}/{(len(todo) + 99) // 100} got {len(seen)}/{len(b)}", flush=True)
        time.sleep(1)
print(time.strftime("%H:%M:%S"), "DONE", flush=True)
