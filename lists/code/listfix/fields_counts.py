"""Turns the build's mismatch list (LISTS_MISMATCHES) into count corrections in list_corrections.json. Run only
after reading the mismatches: each one must follow from a correction already in the file."""
import json, os, sys

P = os.path.expanduser("site/data/phase2/list_corrections.json")
M = json.load(open(sys.argv[1]))
C = json.load(open(P))
L = json.load(open(os.path.expanduser("site/data/phase2/lists.json")))
names = {a["orcid"]: a["name"] for a in L["authors"]}
SRC = "Recount by tools/lists.py after the corrections in this file"
RECOUNT = ("Recount after the corrections in this file: notice dates, citing papers published before the retraction, and "
           "retractions not about the results left out.")
WHY = {"papers": RECOUNT, "journals": RECOUNT, "authors": RECOUNT}
have = {f["path"]: f for f in C["fields"]}
for m in M:
    k = m["path"].split("/")[0]
    if m["path"].endswith("/rank") and m["got"] == "below the cut":
        ident = m["path"].split("/")[1]
        have[f"{k}/{ident}"] = {"path": f"{k}/{ident}", "remove": True, "old": ident, "source": SRC, "date": "2026-10-21",
                                "reason": "Below the cut once the corrections are counted."}
        continue
    prev = have.get(m["path"])
    old = prev["old"] if prev else m["want"]
    have[m["path"]] = {"path": m["path"], "old": old, "new": m["got"], "source": SRC, "date": "2026-10-21", "reason": WHY[k]}
gone = [f["path"] + "/" for f in have.values() if f.get("remove")]  # a removed entry needs no count corrections
C["fields"] = [f for f in have.values() if not any(f["path"].startswith(g) for g in gone)]
json.dump(C, open(P, "w"), indent=1, ensure_ascii=False)
print("fields", len(C["fields"]))
