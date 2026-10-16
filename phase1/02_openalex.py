#!/usr/bin/env python3
"""Step 2: resolve retracted works (nature=Retraction, DOI, retraction year<=2024)
in OpenAlex via the polite pool, batched filter=doi: (50 DOIs/request).
Raw per-batch responses are gzipped to data/openalex_raw/ for reproducibility.
Output: data/openalex_works.jsonl (one row per resolved DOI) + data/openalex_summary.json.
Resumable: skips batches whose raw file already exists.
"""
import os
import gzip, json, sys, time
from pathlib import Path
from urllib.parse import quote
import urllib.request, urllib.error

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
RAWDIR = DATA / "openalex_raw"
RAWDIR.mkdir(parents=True, exist_ok=True)
MAILTO = os.environ.get("SANECITE_MAILTO", "hi@saneapps.com")  # OpenAlex/Crossref polite pool
OA_KEY = os.environ.get("OPENALEX_API_KEY", "")  # optional; OpenAlex limits keyless use to about 1,000 calls a day
SELECT = "id,doi,cited_by_count,counts_by_year,is_retracted,publication_year,title,primary_location"
BATCH = 50

works = [json.loads(l) for l in open(DATA / "works_retracted_le2024.jsonl")]
dois = sorted({w["doi"] for w in works})
print(f"input rows: {len(works)}; unique DOIs: {len(dois)}", flush=True)

def fetch(url, tries=7):
    if OA_KEY and "api.openalex.org" in url: url += ("&" if "?" in url else "?") + "api_key=" + OA_KEY
    req = urllib.request.Request(url, headers={"User-Agent": f"SaneCite-census/1.1 (https://sanecite.com; mailto:{MAILTO})"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(20 * (i + 1)); continue
            raise
        except Exception:
            if i == tries - 1: raise
            time.sleep(10 * (i + 1))
    raise RuntimeError("unreachable")

n_batches = (len(dois) + BATCH - 1) // BATCH
for b in range(n_batches):
    out = RAWDIR / f"batch_{b:04d}.json.gz"
    if out.exists():
        continue
    chunk = dois[b * BATCH:(b + 1) * BATCH]
    filt = "|".join(quote(d, safe="") for d in chunk)
    url = (f"https://api.openalex.org/works?filter=doi:{filt}"
           f"&select={SELECT}&per-page={BATCH}&mailto={MAILTO}")
    try:
        data = fetch(url)
    except Exception as e:
        print(f"batch {b} FAILED: {e}", flush=True)
        continue
    with gzip.open(out, "wt") as f:
        json.dump({"requested_dois": chunk, "response": data}, f)
    if b % 100 == 0:
        print(f"batch {b}/{n_batches} done (count={data.get('meta',{}).get('count')})", flush=True)
    time.sleep(1.0)

# Combine
resolved = {}
files = sorted(RAWDIR.glob("batch_*.json.gz"))
for fp in files:
    with gzip.open(fp, "rt") as f:
        payload = json.load(f)
    for res in payload["response"].get("results", []):
        d = (res.get("doi") or "").replace("https://doi.org/", "").lower()
        if d:
            resolved[d] = res
with open(DATA / "openalex_works.jsonl", "w") as f:
    for d, res in resolved.items():
        f.write(json.dumps(res) + "\n")

summary = {
    "input_rows": len(works),
    "unique_dois": len(dois),
    "batches": len(files),
    "resolved_dois": len(resolved),
    "coverage_pct": round(100.0 * len(resolved) / len(dois), 2) if dois else 0,
}
with open(DATA / "openalex_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2), flush=True)
