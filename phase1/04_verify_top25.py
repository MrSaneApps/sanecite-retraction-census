#!/usr/bin/env python3
"""Step 3: verify the top 25 zombies against Crossref.
For each DOI: GET api.crossref.org/works/<doi> (raw saved to data/crossref_verify/),
extract update-to events; a retraction event = any update-to entry whose type
contains 'retract'. Compare with OpenAlex is_retracted and the RW record.
Disagreements are recorded verbatim in 'discrepancy', never smoothed over.
Output: data/top25_verified.json
"""
import os
import json, time
from pathlib import Path
from urllib.parse import quote
import urllib.request, urllib.error

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
VDIR = DATA / "crossref_verify"
VDIR.mkdir(parents=True, exist_ok=True)
MAILTO = os.environ.get("SANECITE_MAILTO", "hi@saneapps.com")  # OpenAlex/Crossref polite pool
OA_KEY = os.environ.get("OPENALEX_API_KEY", "")  # optional; OpenAlex limits keyless use to about 1,000 calls a day

top50 = json.load(open(DATA / "top50.json"))
top25 = top50[:25]

def fetch(url, tries=4):
    if OA_KEY and "api.openalex.org" in url: url += ("&" if "?" in url else "?") + "api_key=" + OA_KEY
    req = urllib.request.Request(url, headers={
        "User-Agent": f"SaneCite-census/1.1 (https://sanecite.com; mailto:{MAILTO})"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** i * 2); continue
            if e.code == 404:
                return None
            raise
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 ** i)

out = []
for t in top25:
    doi = t["doi"]
    raw_path = VDIR / (doi.replace("/", "_") + ".json")
    if raw_path.exists():
        msg = json.load(open(raw_path))
    else:
        resp = fetch(f"https://api.crossref.org/works/{quote(doi, safe='')}?mailto={MAILTO}")
        msg = resp.get("message") if resp else None
        json.dump(msg, open(raw_path, "w"), indent=1)
        time.sleep(0.3)
    updates = []
    cr_retraction = False
    if msg:
        # The retraction event on the original work's record lives in
        # 'updated-by' (source: retraction-watch / publisher); 'update-to'
        # appears on some records as well. Check BOTH — checking only
        # 'update-to' produced false discrepancies in the first pass.
        for field in ("updated-by", "update-to"):
            for u in msg.get(field, []) or []:
                updates.append({"field": field, "doi": u.get("DOI"), "type": u.get("type"),
                                "label": u.get("label"), "source": u.get("source")})
                if "retract" in (u.get("type") or "").lower():
                    cr_retraction = True
    oa_flag = t["openalex_is_retracted"]
    disc = ""
    if not cr_retraction and oa_flag is not True:
        disc = "NEITHER Crossref (updated-by/update-to) nor OpenAlex is_retracted confirms retraction; only the Retraction Watch record does."
    elif not cr_retraction:
        disc = "Crossref work record carries NO retraction event in updated-by/update-to, but OpenAlex is_retracted=true and RW records a retraction."
    elif oa_flag is not True:
        disc = f"Crossref carries a retraction update event, but OpenAlex is_retracted={oa_flag}."
    out.append({
        **t,
        "crossref_found": msg is not None,
        "crossref_retraction_event": cr_retraction,
        "crossref_update_to": updates,
        "discrepancy": disc,
    })
    print(f"{doi}: crossref_retraction={cr_retraction} openalex={oa_flag} post={t['post_retraction_citations']} disc={'YES' if disc else 'no'}")

with open(DATA / "top25_verified.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"discrepancies: {sum(1 for o in out if o['discrepancy'])}")
