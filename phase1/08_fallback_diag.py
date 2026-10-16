#!/usr/bin/env python3
"""Step 6b: bound the hop-2 fallback distortion in downstream.json.

For each zombie, hop-1 works that lacked counts_by_year contributed their
all-time cited_by_count to hop2_citations. From the cached hop-1 sweeps,
compute exactly: how many of those fallback works have cited_by_count > 0
and the sum they contribute. Amends each downstream record with
fallback_works, fallback_nonzero_works, fallback_citation_sum, so the write-up
can state the bound numerically instead of hand-waving it.
Population matches 07_downstream.py: notice-type citers (is_notice, flagged
in the cache by 07) never contribute to hop-2, so they are excluded here
too; caches written before the flag existed simply lack the key and are
treated as all-research, as before.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
RAW = DATA / "downstream_raw"

ds = json.load(open(DATA / "downstream.json"))
for rec in ds:
    wdir = RAW / rec["doi"].replace("/", "_")
    hop1 = json.load(open(wdir / "hop1_done.json"))
    fb = [h for h in hop1 if not h.get("counts_by_year") and not h.get("is_notice")]
    rec["fallback_works"] = len(fb)
    rec["fallback_nonzero_works"] = sum(1 for h in fb if (h.get("cited_by_count") or 0) > 0)
    rec["fallback_citation_sum"] = sum(h.get("cited_by_count") or 0 for h in fb)
    print(f"#{rec['rank']} {rec['doi']}: fallback {len(fb)} works, "
          f"{rec['fallback_nonzero_works']} nonzero, sum={rec['fallback_citation_sum']} "
          f"of hop2={rec['hop2_citations']}")

with open(DATA / "downstream.json", "w") as f:
    json.dump(ds, f, indent=2)
print("amended data/downstream.json")
