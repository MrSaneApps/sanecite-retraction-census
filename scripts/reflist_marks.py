#!/usr/bin/env python3
"""Post-hoc check (20 Oct 2026, not in the registered protocol): is "the citing paper's own reference list says
retracted" a real retraction mark? A judged headline pair is flagged when "retract" appears anywhere in the citing
paper's reference entry for the target (stage 2, extract.py). sensitivity.py (amendment 3) already sorts those
entries into "title prefix", "retraction note" and "other" with the regexes copied below; this script adds the
support and flagged rates for each kind and for the clear marks (title prefix + retraction note) together.
Reads the public data files. usage: python3 scripts/reflist_marks.py > data/reflist_marks.json"""
import collections, gzip, json, os, re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
ADMIN = "administrative (no fault found in the science)"


def lines(name):
    with gzip.open(os.path.join(DATA, name), "rt", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


rows = {r["pair_id"]: r for r in lines("census_rows.jsonl.gz")}
entry = {r["pair_id"]: r.get("ref_entry") for r in lines("stage2_v31.jsonl.gz") if r.get("pair_id") in rows}
judged = [r for r in rows.values() if r["label"] != "unclear" and r["reason"] != ADMIN]


def kind(pair_id):  # the same rule as sensitivity.py, amendment 3
    e = str(entry.get(pair_id) or "").lower()
    m = re.search(r".{0,25}retract.{0,30}", e, re.S)
    t = m.group(0) if m else ""
    if re.search(r"retracted\s*(article)?\s*[:\]]|\[retracted|retracted article|\bretracted\b\s*[“\"]", t):
        return "title prefix"
    if re.search(r"retraction (in|of|notice)|retracted in|retracted (on|by)|erratum", t):
        return "retraction note"
    return "other"


groups = collections.defaultdict(collections.Counter)
for r in judged:
    if r.get("ref_retracted"):
        groups[kind(r["pair_id"])][r["label"]] += 1
groups["clear marks (title prefix + retraction note)"] = groups["title prefix"] + groups["retraction note"]
out = {"note": "Post-hoc, 20 Oct 2026. Judged headline pairs whose reference entry contains 'retract'.", "groups": {}}
for k, c in groups.items():
    n = sum(c.values())
    out["groups"][k] = {"n": n, "substantive": c["substantive"], "aware": c["aware"],
                        "substantive_rate": round(c["substantive"] / n, 6), "aware_rate": round(c["aware"] / n, 6)}
print(json.dumps(out, indent=1))
