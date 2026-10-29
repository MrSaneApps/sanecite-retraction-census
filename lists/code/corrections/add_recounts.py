#!/usr/bin/env python3
"""Turns the build mismatches (LISTS_MISMATCHES output) into recount entries in list_corrections.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.expanduser("site/data/phase2/list_corrections.json")
F = json.load(open(PATH))
M = json.load(open(sys.argv[1]))
WHY = {"32356626": "One support citation, PMC7836849, went online on 3 Jun 2020, the day before the retraction notice (Gate 15).",
       "19772305": "One support citation, PMC3555345, went online on 20 Jul 2012, before the retraction notice of 20 Aug 2012 (Gate 15).",
       "15833829": "One passing mention, PMC3918054, went online on 13 Jul 2010, before the retraction notice of 14 Aug 2010 (Gate 15).",
       "19918075": "One passing mention, PMC5377414, went online on 8 Oct 2016, before the retraction notice of 19 Dec 2016 (Gate 15).",
       "12609035": "One support citation, PMC4762519, went online on 6 Nov 2015, before the retraction notice of 13 Nov 2015 (Gate 15)."}
JWHY = ("Recounted after the 22 Oct corrections: Life Sci retractions dated by their 2023 notices, Zhang B (Oncogene) dated 2011, "
        "and citations published online before the retraction left out (Gate 1, Gate 15).")
# earlier entries for the same path stay as the record; each one names the value it expects, so they chain in order
done = {(f["path"], json.dumps(f.get("old")), json.dumps(f.get("new"))) for f in F["fields"]}
M = [m for m in M if (m["path"], json.dumps(m["want"]), json.dumps(m["got"])) not in done]
for m in M:
    k = m["path"].split("/")
    F["fields"].append({"path": m["path"], "old": m["want"], "new": m["got"], "source": "Recount by tools/lists.py after the corrections in this file",
                        "date": "2026-10-22", "reason": WHY.get(k[1], JWHY) if k[0] == "papers" else JWHY})
open(PATH, "w").write(json.dumps(F, indent=1, ensure_ascii=False))
print(len(M), "recount entries")
