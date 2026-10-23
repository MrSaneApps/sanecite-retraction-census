#!/usr/bin/env python3
"""Re-check the retraction status of every retracted paper the Lists name, and report what changed.

usage: recheck_retractions.py [--pmids P1,P2,...] [--limit N] [--out report.json] [--save]

A retraction can be reversed, replaced by a corrected article under the same DOI, or downgraded to an expression of
concern after we name a paper. This script asks two independent sources again for each listed PMID:
  PubMed (NCBI E-utilities esummary): is the record still typed "Retracted Publication"?
  Crossref (REST /works/<doi>): which notices does "updated-by" list now (retraction, expression of concern,
  correction, withdrawal, ...)?
and compares the PubMed answer with lists/data/retraction_status.csv, the status the Lists were built on, and the
Crossref answer with the previous run (errata/retraction_recheck_state.json, written only with --save). Many publishers never
deposit "updated-by", so an empty Crossref answer is a note, not a change; a notice type that appears or disappears
between runs is a change.

Listed PMIDs = the papers on the Lists, the retracted papers in author entries, and every retracted paper with a
citation in the second reading (lists/data/lists.json, author_items.json, list_checks.csv).

Output: one line per paper whose status differs from the baseline, then a summary; --out writes every answer as
JSON. Exit code 0 when nothing changed, 3 when something did (so a monthly job can open a correction item), 2 on a
lookup failure. Read-only: it never edits the Lists. Free public APIs, about one request a second.
"""
import argparse, csv, json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "lists", "data")
UA = {"User-Agent": "sanecite-recheck/1.0 (mailto:hi@saneapps.com)"}


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            err = e
        except Exception as e:  # network error: wait and retry, then give up loudly
            err = e
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"{url}: {err}")


def listed_pmids():
    lists = json.load(open(os.path.join(DATA, "lists.json")))
    out = {str(p["pmid"]) for p in lists.get("papers", [])}
    out |= set(json.load(open(os.path.join(DATA, "author_items.json"))).get("cited", {}))
    for r in csv.DictReader(open(os.path.join(DATA, "list_checks.csv"))):
        if r.get("retracted_pmid"): out.add(r["retracted_pmid"])
    return sorted(out, key=int)


def baseline():
    return {r["retracted_pmid"]: r for r in csv.DictReader(open(os.path.join(DATA, "retraction_status.csv")))}


def pubmed(pmids):
    out = {}
    for i in range(0, len(pmids), 200):
        q = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids[i:i + 200]), "retmode": "json"})
        res = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + q).get("result", {})
        for p in pmids[i:i + 200]:
            r = res.get(p) or {}
            doi = next((a["value"] for a in r.get("articleids", []) if a.get("idtype") == "doi"), "")
            out[p] = {"pubtypes": r.get("pubtype", []), "doi": doi.lower(), "found": bool(r) and "error" not in r}
        time.sleep(0.4)
    return out


def crossref(doi):
    if not doi: return None
    msg = (get("https://api.crossref.org/works/" + urllib.parse.quote(doi)) or {}).get("message") or {}
    ups = msg.get("updated-by") or []
    return sorted({u.get("type", "?") for u in ups})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pmids", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--save", action="store_true", help="store this run's Crossref answers as the next run's baseline")
    a = ap.parse_args()
    pmids = [p.strip() for p in a.pmids.split(",") if p.strip()] or listed_pmids()
    if a.limit: pmids = pmids[:a.limit]
    base = baseline()
    state_path = os.path.join(ROOT, "errata", "retraction_recheck_state.json")  # outside lists/, which stage_release.py rebuilds
    prev = json.load(open(state_path)) if os.path.exists(state_path) else {}
    try:
        pm = pubmed(pmids)
        rows, changed = [], 0
        for p in pmids:
            b = (base.get(p) or {}).get("pubmed_status", "not in baseline")
            r = pm[p]
            cr = crossref(r["doi"]); time.sleep(1)
            pub_retracted = "Retracted Publication" in r["pubtypes"]
            was_retracted = b.startswith("retracted")
            notes, info = [], []
            if was_retracted and not pub_retracted: notes.append("PubMed no longer types it Retracted Publication")
            if not was_retracted and pub_retracted: notes.append("PubMed now types it Retracted Publication")
            if not r["found"]: notes.append("PubMed record not found")
            if p in prev and cr is not None and prev[p] is not None and set(cr) != set(prev[p]):
                notes.append(f"Crossref updated-by changed: {', '.join(prev[p]) or 'none'} -> {', '.join(cr) or 'none'}")
            if cr and ("expression_of_concern" in cr or any("reinstat" in t or "restor" in t for t in cr)) and (prev.get(p) or []) != cr:
                notes.append("Crossref lists " + ", ".join(t for t in cr if t not in ("retraction", "erratum", "correction")))
            if cr == []: info.append("no Crossref update record (publisher deposits none)")
            if cr is None: info.append("no DOI in PubMed" if not r["doi"] else "DOI not in Crossref")
            row = {"pmid": p, "baseline": b, "pubmed_pubtypes": r["pubtypes"], "doi": r["doi"], "crossref_updated_by": cr,
                   "changes": notes, "notes": info}
            rows.append(row)
            if notes:
                changed += 1; print(f"{p}\t{b}\t" + "; ".join(notes))
    except RuntimeError as e:
        print("lookup failed:", e); sys.exit(2)
    print(f"checked {len(rows)} listed PMIDs; {changed} changed; {sum(1 for r in rows if r['notes'])} with notes only")
    if a.save:
        prev.update({r["pmid"]: r["crossref_updated_by"] for r in rows})
        json.dump(prev, open(state_path, "w"), indent=0, sort_keys=True)
    if a.out: json.dump({"checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": rows}, open(a.out, "w"), indent=1)
    sys.exit(3 if changed else 0)


if __name__ == "__main__":
    main()
