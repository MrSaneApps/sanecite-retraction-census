"""Puts named lists.json fields back to the generated value a correction expects, so a changed correction can apply."""
import json, os, sys
SITE = os.path.expanduser("site/data/phase2")
C = json.load(open(f"{SITE}/list_corrections.json"))
L = json.load(open(f"{SITE}/lists.json"))
F = {f["path"]: f for f in C["fields"]}
for path in sys.argv[1:]:
    k, pmid, field = path.split("/")
    p = next(x for x in L["papers"] if x["pmid"] == pmid)
    if F[path]["old"] is None: p.pop(field, None)
    else: p[field] = F[path]["old"]
json.dump(L, open(f"{SITE}/lists.json", "w"), indent=1)
print("reset", len(sys.argv) - 1)
