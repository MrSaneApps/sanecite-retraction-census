#!/usr/bin/env python3
"""Step 4: sanity gate — 10 random mid-table works, re-checked by hand against
fresh single-work API calls (independent of the batch pulls).
Mid-table = resolved works whose post-retraction citation rank falls in the
middle 50% (25th–75th percentile of the ranked list), excluding the top 50.
Seed fixed at 20261013 for reproducibility.
Checks per work: fresh OpenAlex single-work cited_by_count + counts_by_year
recompute vs batch values; OpenAlex is_retracted vs Crossref update-to event.
Output: data/sanity_checks.json
"""
import os
import json, random, time
from pathlib import Path
from urllib.parse import quote
import urllib.request, urllib.error

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
MAILTO = os.environ.get("SANECITE_MAILTO", "hi@saneapps.com")  # OpenAlex/Crossref polite pool
OA_KEY = os.environ.get("OPENALEX_API_KEY", "")  # optional; OpenAlex limits keyless use to about 1,000 calls a day

rows = [json.loads(l) for l in open(DATA / "per_work.jsonl")]
res = [r for r in rows if r.get("resolved")]
res.sort(key=lambda r: -r["post_retraction_citations"])
n = len(res)
mid = res[int(0.25 * n): int(0.75 * n)]
random.seed(20261013)
sample = random.sample(mid, 10)

def fetch_json(url, tries=4):
    if OA_KEY and "api.openalex.org" in url: url += ("&" if "?" in url else "?") + "api_key=" + OA_KEY
    req = urllib.request.Request(url, headers={
        "User-Agent": f"SaneCite-census/1.1 (https://sanecite.com; mailto:{MAILTO})"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** i * 2); continue
            raise
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 ** i)

checks = []
for s in sample:
    doi = s["doi"]; ry = s["retraction_year"]
    oa = fetch_json(f"https://api.openalex.org/works/doi:{quote(doi, safe='')}?mailto={MAILTO}")
    time.sleep(0.3)
    cr_resp = fetch_json(f"https://api.crossref.org/works/{quote(doi, safe='')}?mailto={MAILTO}")
    time.sleep(0.3)
    cr = cr_resp.get("message") if cr_resp else None
    fresh_post = None; fresh_total = None; fresh_flag = None
    if oa:
        cby = {c["year"]: c["cited_by_count"] for c in oa.get("counts_by_year", [])}
        fresh_post = sum(c for y, c in cby.items() if y > ry)
        fresh_total = oa.get("cited_by_count")
        fresh_flag = oa.get("is_retracted")
    cr_retr = False
    if cr:
        cr_retr = any("retract" in (u.get("type") or "").lower()
                      for field in ("updated-by", "update-to")
                      for u in (cr.get(field) or []))
    checks.append({
        "doi": doi, "retraction_year": ry,
        "batch_post": s["post_retraction_citations"], "fresh_post": fresh_post,
        "post_match": fresh_post == s["post_retraction_citations"],
        "batch_total_cited_by": s["total_cited_by"], "fresh_total_cited_by": fresh_total,
        "total_match": fresh_total == s["total_cited_by"],
        "batch_is_retracted": s["openalex_is_retracted"], "fresh_is_retracted": fresh_flag,
        "crossref_retraction_event": cr_retr,
        "sources_agree_on_retraction": (fresh_flag is True) == cr_retr,
    })
    c = checks[-1]
    print(f"{doi}: post {c['batch_post']}=={c['fresh_post']} {c['post_match']}; total match {c['total_match']}; OA flag {fresh_flag}; CR event {cr_retr}")

with open(DATA / "sanity_checks.json", "w") as f:
    json.dump(checks, f, indent=2)
ok = sum(1 for c in checks if c["post_match"] and c["total_match"])
print(f"sanity: {ok}/10 exact matches on counts")
