#!/usr/bin/env python3
"""Display data for the author list's items, for the SaneCite Lists page: each citing paper's title, journal, year
and whether Europe PMC types it as a review, and each cited retracted work's first author, journal, year, title and
the retraction year printed in the 21 Oct 2026 author letters (checked against the notices in
WAVE3_VERIFICATION_2026-10-21.md; later corrections live in the site's list_corrections.json, not here).
No email addresses or other contact data are copied.
usage: python3 author_items.py <top10 dir> <site data/phase2 dir>"""
import glob, html, json, re, sys, time, urllib.parse, urllib.request

T, P2 = sys.argv[1], sys.argv[2]
L = json.load(open(f"{T}/letters/authors_letters.json"))


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s or ""))
    return re.sub(r"^(RETRACTED|Retracted|Retraction)[:.]\s*", "", s).strip().rstrip(".")


# retraction year as printed in the sent letters, keyed by cited work (first author, journal, year)
printed = {}
for f in glob.glob(f"{T}/letters/out/author-*.txt"):
    for line in open(f):
        m = re.match(r'\s+cites: (.*?) et al\., (.+?)(?: (\d{4}))?, retracted (\d{4}): "(.*)"(?: \[.*\])?$', line.rstrip("\n"))
        if m:
            printed.setdefault((m.group(1), m.group(2), m.group(3) or ""), set()).add(m.group(4))
citing, cited = {}, {}
for a in L:
    for p in a["papers"]:
        citing[p["pmcid"]] = {"title": clean(p["title"]), "journal": p["journal"], "year": p["year"]}
        for c in p["cites"]:
            ys = set(printed.get((c["first_author"] or "", c["journal"], c["year"] or ""), set()))
            assert len(ys) <= 1, ("two printed years for one work", c["pmid"], ys)
            cited[c["pmid"]] = {"first_author": c["first_author"], "journal": c["journal"], "year": c["year"],
                                "title": clean(c["title"]), "retraction_year": ys.pop() if ys else ""}
ids = sorted(citing)
for i in range(0, len(ids), 100):
    q = " OR ".join(f"PMCID:{x}" for x in ids[i:i + 100])
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "resultType": "core", "format": "json", "pageSize": 1000})
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SaneCite research (hi@saneapps.com)"}), timeout=60))
    for r in d["resultList"]["result"]:
        if r.get("pmcid") in citing:
            citing[r["pmcid"]]["review"] = any("review" in t.lower() for t in (r.get("pubTypeList") or {}).get("pubType", []))
    time.sleep(1)
missing = [p for p in citing if "review" not in citing[p]]
assert not missing, ("no Europe PMC publication type", missing)
json.dump({"made": time.strftime("%Y-%m-%d"), "source": "outputs/sanecite-top10-20261020/author_items.py from the author letter data",
           "citing": dict(sorted(citing.items())), "cited": dict(sorted(cited.items()))},
          open(f"{P2}/author_items.json", "w"), indent=1, ensure_ascii=False)
print("citing", len(citing), "cited", len(cited), "no printed year", sorted(p for p, c in cited.items() if not c["retraction_year"]))
