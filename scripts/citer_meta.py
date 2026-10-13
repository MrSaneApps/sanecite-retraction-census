#!/usr/bin/env python3
"""Census add-on: metadata for EVERY post-retraction citer (open access or not), from Europe PMC.
Feeds two planned analyses: open-access coverage bias (year, journal, type of the citers we could not read)
and harm by citing-paper type (reviews, systematic reviews, meta-analyses, guidelines, trials).
Same query as stage1_frame.py (citing year >= retraction year + 1), resultType=lite.
Resumable; one JSON line per retracted paper. usage: SANECITE_DATA=... citer_meta.py [workers]"""
import json, os, sys, time, threading, urllib.parse, urllib.request
import concurrent.futures as cf
from datetime import datetime, timezone

DATA = os.environ["SANECITE_DATA"]; OUT = f"{DATA}/citer_meta.jsonl"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
W = int(sys.argv[1]) if len(sys.argv) > 1 else 6

def log(*a): print(datetime.now(timezone.utc).strftime("%H:%M:%S"), *a, flush=True)

def get(params, tries=5):
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SaneCite-Phase2-census (hi@saneapps.com)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            log("retry", i, type(e).__name__, str(e)[:80]); time.sleep(3 * (i + 1))
    raise RuntimeError("failed: " + url)

def one(p):
    base = f"CITES:{p['pmid']}_MED AND PUB_YEAR:[{p['retraction_year'] + 1} TO 2026]"
    citers, cursor = [], "*"
    while True:
        d = get({"query": base, "format": "json", "pageSize": 1000, "resultType": "lite", "cursorMark": cursor})
        res = d.get("resultList", {}).get("result", [])
        for r in res:
            citers.append({"id": r.get("id"), "src": r.get("source"), "pmcid": r.get("pmcid"), "year": r.get("pubYear"),
                           "journal": r.get("journalTitle"), "type": r.get("pubType"), "oa": r.get("isOpenAccess"),
                           "pmc": r.get("inPMC")})
        nxt = d.get("nextCursorMark")
        if not nxt or nxt == cursor or len(res) < 1000: break
        cursor = nxt
    time.sleep(0.1)
    return {"pmid": p["pmid"], "n": len(citers), "citers": citers}

papers = [json.loads(l) for l in open(f"{DATA}/stage1_papers.jsonl")]
todo_all = [p for p in papers if int(p.get("post_retraction_citations_epmc") or 0) > 0]
done = set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)["pmid"])
        except Exception: pass
todo = [p for p in todo_all if p["pmid"] not in done]
log(f"STAGE citer_meta papers={len(todo_all)} todo={len(todo)}")
lock, bad = threading.Lock(), 0
with open(OUT, "a") as f, cf.ThreadPoolExecutor(W) as ex:
    futs = {ex.submit(one, p): p for p in todo}
    for k, fu in enumerate(cf.as_completed(futs)):
        try: rec = fu.result()
        except Exception as e: bad += 1; log("FAIL", futs[fu]["pmid"], str(e)[:80]); continue
        with lock: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if k % 500 == 0: f.flush(); log(f"STAGE citer_meta {k}/{len(todo)} fails={bad}")
log(f"EXIT ok citer_meta fails={bad}")
