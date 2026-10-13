#!/usr/bin/env python3
"""Re-extract every census pair from the gzip XML cache with the current (frozen) extractor.
Fetches only what is missing from the cache. Writes $SANECITE_DATA/stage2_v31.jsonl (resumable by pair_id)."""
import json, os, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__)); import extract as E
DATA = os.environ["SANECITE_DATA"]
papers = [json.loads(l) for l in open(f"{DATA}/stage1_papers.jsonl")]
pairs = [(p, c) for p in papers for c in p["oa_citers"]]
OUT = f"{DATA}/stage2_v31.jsonl"
done = set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)["pair_id"])
        except Exception: pass
def year(p):
    d = p.get("original_date", ""); return int(d.split("/")[-1]) if d.count("/") == 2 and d.split("/")[-1].isdigit() else None
def work(pc):
    p, c = pc
    try:
        x = E.fetch_xml(c["pmcid"])
        res = E.contexts(x, p["pmid"], p["doi"], p["title"], year=year(p)) if x else {"status": "no-fulltext"}
    except Exception as e:
        res = {"status": "error", "error": f"{type(e).__name__}: {str(e)[:120]}"}
    return {"pair_id": f"{p['pmid']}>{c['pmcid']}", "retracted_pmid": p["pmid"], "retracted_title": p["title"], "retracted_doi": p["doi"],
            "retracted_journal": p["journal"], "retraction_year": p["retraction_year"], "original_date": p.get("original_date"),
            "reason": p["reason"], "subject": p["subject"], "citing_pmcid": c["pmcid"], "citing_year": c["year"],
            "citing_journal": c["journal"], "extractor": "v3.1", **res}
todo = [pc for pc in pairs if f"{pc[0]['pmid']}>{pc[1]['pmcid']}" not in done]
print(time.strftime("%H:%M:%S"), f"STAGE reextract pairs={len(pairs)} todo={len(todo)}", flush=True)
with open(OUT, "a") as f, cf.ThreadPoolExecutor(int(os.environ.get("SANECITE_WORKERS", "8"))) as ex:
    for k, r in enumerate(ex.map(work, todo)):
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        if k % 2000 == 0: f.flush(); print(time.strftime("%H:%M:%S"), f"STAGE reextract {k}/{len(todo)}", flush=True)
print(time.strftime("%H:%M:%S"), "EXIT ok", flush=True)
