#!/usr/bin/env python3
"""SOP B1 second source for every retracted work a Lists letter names: Crossref's record for the DOI (updated-by a
retraction, or a title marked retracted). PubMed's linked retraction notice is the first source (lists_data.py).
Writes <letters>/crossref_check.json: doi -> {ok, how}. usage: python3 crossref_check.py <letters dir>"""
import json, sys, time, urllib.parse, urllib.request

D = sys.argv[1]
A = json.load(open(f"{D}/authors_letters.json"))
L = json.load(open(f"{D}/lists.json"))
dois = {c["doi"].lower() for a in A for p in a["papers"] for c in p["cites"] if c.get("doi")}
dois |= {p["doi"].lower() for p in L["papers"] if p.get("doi")}
missing = sorted({c["pmid"] for a in A for p in a["papers"] for c in p["cites"] if not c.get("doi")})
print(f"stage 1: {len(dois)} DOIs, {len(missing)} works without a DOI {missing}", flush=True)
out = {}
for n, doi in enumerate(sorted(dois), 1):
    try:
        m = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://api.crossref.org/works/" + urllib.parse.quote(doi) + "?mailto=hi@saneapps.com",
            headers={"User-Agent": "SaneCite research (mailto:hi@saneapps.com)"}), timeout=60))["message"]
        ups = [u for u in m.get("updated-by", []) + m.get("update-to", []) if "retract" in (u.get("type") or "").lower()
               or "withdraw" in (u.get("type") or "").lower()]
        title = " ".join(m.get("title") or [])
        if ups: out[doi] = {"ok": True, "how": "crossref updated-by " + ",".join(sorted({u.get('type') for u in ups}))
                            + " " + ",".join(sorted({u.get('source', '') for u in ups}))}
        elif "retract" in title.lower(): out[doi] = {"ok": True, "how": "crossref title: " + title[:80]}
        else: out[doi] = {"ok": False, "how": "crossref shows no retraction"}
    except Exception as e:
        out[doi] = {"ok": False, "how": f"crossref error {type(e).__name__}"}
    if n % 25 == 0: print(f"stage 2: {n}/{len(dois)}", flush=True)
    time.sleep(0.3)
bad = {k: v for k, v in out.items() if not v["ok"]}
json.dump(out, open(f"{D}/crossref_check.json", "w"), indent=1)
print(f"stage 3: {len(out) - len(bad)} confirmed by Crossref, {len(bad)} not:", flush=True)
for k, v in bad.items(): print("  ", k, v["how"], flush=True)
print("EXIT ok", flush=True)
