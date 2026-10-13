#!/usr/bin/env python3
"""Phase 2 pilot, stage 1: draw a simple random sample of retracted papers and
enumerate the open-access papers in Europe PMC that cited each one AFTER its
retraction year. Resumable; writes one JSON line per sampled retracted paper.

Frame: Retraction Watch (via Crossref) records with RetractionNature=Retraction,
an original-paper PubMed ID, retracted 1990-2023 (so every paper has >=2 full
calendar years of post-retraction exposure). Deduplicated by PMID.
"""
import csv, json, os, random, sys, threading, time, urllib.parse, urllib.request
import concurrent.futures as cf
from datetime import datetime, timezone

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED, ARG = 20261013, (sys.argv[1] if len(sys.argv) > 1 else "2500")
# SANECITE_DATA points a full-corpus run at its own data dir; "all" = census of the frame.
DATA = os.environ.get("SANECITE_DATA", f"{D}/data")
OUT = f"{DATA}/stage1_papers.jsonl"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

def log(*a): print(datetime.now(timezone.utc).strftime("%H:%M:%S"), *a, flush=True)

def get(params, tries=4):
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SaneCite-Phase2-pilot (hi@saneapps.com)"}), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            log("retry", i, type(e).__name__, str(e)[:80]); time.sleep(2 * (i + 1))
    raise RuntimeError("failed: " + url)

frame, seen = [], set()
for x in csv.DictReader(open(f"{D}/data/retraction_watch.csv", encoding="utf-8", errors="replace")):
    pmid = (x["OriginalPaperPubMedID"] or "").strip()
    if x["RetractionNature"] != "Retraction" or pmid in ("", "0") or pmid in seen: continue
    try: ry = datetime.strptime(x["RetractionDate"].split()[0], "%m/%d/%Y").year
    except Exception: continue
    if not 1990 <= ry <= 2023: continue
    seen.add(pmid)
    frame.append({"rw_id": x["Record ID"], "pmid": pmid, "doi": x["OriginalPaperDOI"].strip().lower(),
                  "title": x["Title"], "journal": x["Journal"], "subject": x["Subject"],
                  "retracted": x["RetractionDate"].split()[0], "retraction_year": ry,
                  "original_date": x["OriginalPaperDate"].split()[0], "reason": x["Reason"]})
frame.sort(key=lambda r: int(r["pmid"]))
N = len(frame) if ARG == "all" else int(ARG)
sample = list(frame) if ARG == "all" else random.Random(SEED).sample(frame, N)
log(f"frame={len(frame)} sample={N} seed={SEED}")
json.dump({"frame_size": len(frame), "sample_size": N, "seed": SEED,
           "rule": "RetractionNature=Retraction, has original PMID, retracted 1990-2023, dedup by PMID, sorted by PMID then random.Random(seed).sample"},
          open(f"{DATA}/stage1_meta.json", "w"), indent=1)

done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["pmid"] for l in open(OUT)}
log("resuming, already done:", len(done))
def one(p):
    y0 = p["retraction_year"] + 1
    base = f"CITES:{p['pmid']}_MED AND PUB_YEAR:[{y0} TO 2026]"
    allpost = get({"query": base, "format": "json", "pageSize": 1, "resultType": "idlist"}).get("hitCount", 0)
    citers, cursor = [], "*"
    if allpost:
        while True:
            d = get({"query": base + " AND OPEN_ACCESS:y AND HAS_FT:y", "format": "json", "pageSize": 1000,
                     "resultType": "lite", "cursorMark": cursor})
            for r in d.get("resultList", {}).get("result", []):
                if r.get("pmcid"):
                    citers.append({"pmcid": r["pmcid"], "pmid": r.get("pmid"), "doi": (r.get("doi") or "").lower(),
                                   "year": r.get("pubYear"), "title": r.get("title"), "journal": r.get("journalTitle")})
            nxt = d.get("nextCursorMark")
            if not nxt or nxt == cursor or len(d.get("resultList", {}).get("result", [])) < 1000: break
            cursor = nxt
    time.sleep(0.12)
    return dict(p, post_retraction_citations_epmc=allpost, oa_citers=citers)

todo = [p for p in sample if p["pmid"] not in done]
lock = threading.Lock()
with open(OUT, "a") as f, cf.ThreadPoolExecutor(max_workers=int(os.environ.get("SANECITE_WORKERS", "1"))) as ex:
    for k, fu in enumerate(cf.as_completed([ex.submit(one, p) for p in todo])):
        try: p = fu.result()
        except Exception as e: log("FAIL", str(e)[:120]); continue  # rerun resumes the missing PMIDs
        with lock: f.write(json.dumps(p, ensure_ascii=False) + "\n"); f.flush()
        if k % 250 == 0: log(f"STAGE {k}/{len(todo)} pmid={p['pmid']} post={p['post_retraction_citations_epmc']} oa={len(p['oa_citers'])}")
log("EXIT ok")
