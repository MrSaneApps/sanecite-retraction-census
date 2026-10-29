"""Writes lists.json and author_items.json with list_corrections.json applied, to the site and the source copy."""
import json, os, shutil, sys
SITE = os.path.expanduser("site")
sys.path.insert(0, f"{SITE}/tools")
os.chdir(SITE)
import lists  # applies every correction and runs every check; stops on any mismatch
json.dump(lists.L, open(f"{SITE}/data/phase2/lists.json", "w"), indent=1)
json.dump(lists.ITEMS, open(f"{SITE}/data/phase2/author_items.json", "w"), indent=1, ensure_ascii=False)
src = os.path.expanduser("work/top10/letters/lists.json")
shutil.copyfile(f"{SITE}/data/phase2/lists.json", src)
print("wrote", len(lists.L["papers"]), "papers", len(lists.L["authors"]), "authors")
