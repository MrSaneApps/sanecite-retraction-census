#!/usr/bin/env python3
"""Frame correction of amendment 11 (part 4): find Retraction Watch records whose PubMed ID points to a different paper.

usage: frame_check.py [--fetch]
  reads   data/stage1_papers.jsonl.gz  (Retraction Watch title, DOI and PMID of each frame record)
          data/census_rows.jsonl.gz    (the census pairs, to list the pairs each wrong record carries)
          errata/epmc_titles.jsonl.gz  (Europe PMC title, DOI and year for each PMID; --fetch adds any that are missing)
  writes  errata/wrong_records.csv         one row per wrong record that carries census pairs
          errata/explained_mismatches.csv  title mismatches that the rule explains (not wrong records)

Rule (PROTOCOL.md, amendment 11, part 4). A record is a WRONG RECORD when Europe PMC's title for the PMID shares under
half the words of the Retraction Watch title (overlap over the shorter title, words over 3 letters), unless:
  (a) same DOI and overlap >= 0.3 (a translated or re-titled record of the same article), or a bracketed (translated)
      PubMed title with the same publication year;
  (b) the PubMed record was replaced by its own retraction, withdrawal or erratum notice under the same DOI;
  (c) the Retraction Watch title is generic ("Editorial", "Response to commentary") and the DOI is the same.
Whole meeting-abstract supplements are wrong records whatever their DOI, because their citations cannot be attributed
to one abstract.

Scope of this file: the 12,864 retracted papers that have a pair in the census (the Europe PMC titles were pulled on
20 Oct 2026). The full frame scan of amendment 11 covered all 22,553 records and found 70 wrong records (86 later
citations); 12 of those citations are census pairs, the ones listed here. analyze_census.py reads wrong_records.csv
and reports the census both as published and without these pairs.
"""
import csv, gzip, json, os, re, sys, time, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERR = os.path.join(ROOT, "errata")
TITLES = os.path.join(ERR, "epmc_titles.jsonl.gz")

def jsonl(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        return [json.loads(l) for l in f if l.strip()]

def words(s):
    return {w for w in re.findall(r"[a-z0-9]+", re.sub(r"<[^>]+>", "", s or "").lower()) if len(w) > 3}

def overlap(a, b):
    A, B = words(a), words(b)
    return len(A & B) / max(1, min(len(A), len(B)))

NOTICE = re.compile(r"^\s*(retraction|retracted|withdrawal|withdrawn|erratum|correction|corrigendum|notice of retraction|expression of concern)\b", re.I)
GENERIC = re.compile(r"^\s*(editorial|response to (the )?commentary|reply|letter|comment|commentary|abstract|abstracts)\s*\.?\s*$", re.I)
MEETING = re.compile(r"\b(abstracts?|annual meeting|congress|conference|symposium|proceedings)\b", re.I)

def judge(rw, ep):
    """(is_wrong, reason) for one record whose titles were compared; None when the titles agree."""
    s = overlap(rw["title"], ep.get("title"))
    rdoi, edoi = (rw.get("doi") or "").lower().strip(), (ep.get("doi") or "").lower().strip()
    same_doi = bool(rdoi and rdoi == edoi)
    et = ep.get("title") or ""
    if s >= 0.5: return None, s
    if same_doi and MEETING.search(et) and not MEETING.search(rw["title"]):
        return (True, "meeting-abstract supplement"), s
    if same_doi and s >= 0.3: return (False, "(a) same DOI, re-titled or translated record"), s
    if et.strip().startswith("[") and str(ep.get("year")) == str(rw.get("pub_year") or ""):
        return (False, "(a) bracketed translated title, same year"), s
    if same_doi and NOTICE.search(et): return (False, "(b) PubMed record replaced by its own notice, same DOI"), s
    if same_doi and GENERIC.search(rw["title"]): return (False, "(c) generic Retraction Watch title, same DOI"), s
    return (True, "different paper" if not same_doi else "same DOI, different title"), s

def fetch(pmids):
    """Europe PMC REST search, 100 PMIDs per request, one request per second (free, read-only)."""
    out = []
    for i in range(0, len(pmids), 100):
        chunk = pmids[i:i + 100]
        q = "(" + " OR ".join("EXT_ID:" + p for p in chunk) + ") AND SRC:MED"
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
            {"query": q, "format": "json", "pageSize": 1000, "resultType": "lite"})
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sanecite-census/1.3"}), timeout=60) as r:
            got = {x.get("pmid"): x for x in json.loads(r.read().decode()).get("resultList", {}).get("result", [])}
        for p in chunk:
            x = got.get(p) or {}
            out.append({"q": p, "found": bool(x), "title": x.get("title"), "doi": x.get("doi"), "year": x.get("pubYear")})
        time.sleep(1)
    return out

def main():
    frame = {r["pmid"]: r for r in jsonl(os.path.join(ROOT, "data", "stage1_papers.jsonl.gz"))}
    rows = jsonl(os.path.join(ROOT, "data", "census_rows.jsonl.gz"))
    pairs = {}
    for r in rows: pairs.setdefault(r["paper"], []).append(r["pair_id"])
    ep = {r["q"]: r for r in jsonl(TITLES)} if os.path.exists(TITLES) else {}
    missing = sorted(p for p in pairs if p not in ep)
    if missing:
        if "--fetch" not in sys.argv: sys.exit(f"{len(missing)} census PMIDs have no Europe PMC title; run with --fetch")
        for r in fetch(missing): ep[r["q"]] = r
        with gzip.open(TITLES, "wt") as f:
            for p in sorted(ep): f.write(json.dumps(ep[p], ensure_ascii=False) + "\n")
    wrong, explained = [], []
    for p in sorted(pairs, key=int):
        rw, e = frame.get(p), ep.get(p)
        if not rw or not e or not e.get("found"): continue
        v, s = judge({**rw, "pub_year": (rw.get("original_date") or "").split("/")[-1].split(" ")[0]}, e)
        if v is None: continue
        row = {"rw_id": rw.get("rw_id"), "pmid": p, "rw_title": rw["title"], "epmc_title": e.get("title") or "",
               "rw_doi": rw.get("doi") or "", "epmc_doi": e.get("doi") or "", "overlap": f"{s:.2f}", "rule": v[1],
               "n_pairs": len(pairs[p]), "affected_pair_ids": " ".join(sorted(pairs[p]))}
        (wrong if v[0] else explained).append(row)
    os.makedirs(ERR, exist_ok=True)
    for name, data in (("wrong_records.csv", wrong), ("explained_mismatches.csv", explained)):
        with open(os.path.join(ERR, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["rw_id", "pmid", "rw_title", "epmc_title", "rw_doi", "epmc_doi", "overlap",
                                               "rule", "n_pairs", "affected_pair_ids"])
            w.writeheader(); w.writerows(data)
    print(f"census papers checked {len(pairs)}; wrong records {len(wrong)} carrying {sum(r['n_pairs'] for r in wrong)} pairs; "
          f"explained mismatches {len(explained)}")

if __name__ == "__main__":
    main()
