#!/usr/bin/env python3
"""Step 6: downstream trace for the top 25 verified zombies.

HOP 1: works citing the zombie with publication_year > retraction_year
       (OpenAlex filter=cites:<id>,publication_year:>YYYY, full cursor sweep;
        raw pages gzipped to data/downstream_raw/<doi>/).
HOP 2: citations OF the hop-1 works, restricted to years > retraction_year
       via each hop-1 work's counts_by_year. Hop-1 works lacking counts_by_year
       contribute their all-time cited_by_count and are counted as fallbacks;
       hop2_basis labels this per zombie (never present a mixed
       total as a clean restricted one).
SYNTHESIS DETECTION (stated method, a lower bound): a work counts as an
identifiable systematic review / meta-analysis iff its TITLE matches
/systematic review|meta[- ]analys/i, or its OpenAlex concepts include
'Meta-analysis' or 'Systematic review' (hop-1 only). Hop-2 candidates are
generated with OpenAlex search=('meta-analysis'|'systematic review') over
cites:<hop-1 batch> and then confirmed by the same title test locally.
NOTICE EXCLUSION (Phase 2 parity): a hop-1 citer that is itself a
notice-type document (retraction notice, erratum, correction — see
is_notice()) is not a research work relying on the zombie. Such citers are
flagged `is_notice` in the hop1_done.json cache, counted separately as
hop1_notices, and excluded from hop1_count, the hop-2 totals and the
synthesis detection — the same treatment Phase 2's analyze.py gives them
(notices reported apart, rates over research papers only).
Output: data/downstream.json
"""
import os
import gzip, json, re, time
from pathlib import Path
from urllib.parse import quote
import urllib.request, urllib.error

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
RAW = DATA / "downstream_raw"
RAW.mkdir(parents=True, exist_ok=True)
MAILTO = os.environ.get("SANECITE_MAILTO", "hi@saneapps.com")  # OpenAlex/Crossref polite pool
OA_KEY = os.environ.get("OPENALEX_API_KEY", "")  # optional; OpenAlex limits keyless use to about 1,000 calls a day
TITLE_RE = re.compile(r"systematic review|meta[-\s]?analys", re.I)
SYNTH_CONCEPTS = {"Meta-analysis", "Systematic review"}
SELECT1 = "id,doi,title,publication_year,cited_by_count,counts_by_year,type,concepts"

def fetch(url, tries=4):
    if OA_KEY and "api.openalex.org" in url: url += ("&" if "?" in url else "?") + "api_key=" + OA_KEY
    req = urllib.request.Request(url, headers={
        "User-Agent": f"SaneCite-census/1.1 (https://sanecite.com; mailto:{MAILTO})"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** i * 2); continue
            raise
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 ** i)

def is_synthesis(w, use_concepts=True):
    if TITLE_RE.search(w.get("title") or ""):
        return True
    if use_concepts:
        for c in w.get("concepts") or []:
            if c.get("display_name") in SYNTH_CONCEPTS:
                return True
    return False

# Notice-type citer detection — mirrors Phase 2 extract.py's is_notice,
# adapted to the metadata OpenAlex carries for a citing work. Signals,
# strongest first: the citer's DOI is the zombie's own retraction-notice DOI
# (Retraction Watch RetractionDOI, or a Crossref update target on the
# zombie's record whose type contains 'retract'); the citer's OpenAlex type
# is a notice type ('retraction', 'erratum' — the OpenAlex counterparts of
# extract.py's JATS article-types); the citer's title starts with one of
# extract.py's notice prefixes (same regex).
NOTICE_TITLE_RE = re.compile(
    r"(retraction|retracted|expression of concern|correction|erratum|corrigendum|notice of)")
NOTICE_TYPES = {"retraction", "erratum"}

def is_notice(w, notice_dois=()):
    d = (w.get("doi") or "").replace("https://doi.org/", "").lower()
    if d and d in notice_dois:
        return True
    if w.get("type") in NOTICE_TYPES:
        return True
    return bool(NOTICE_TITLE_RE.match((w.get("title") or "").lower()))

def sweep(url_base, outdir, tag):
    """Cursor-paginate a works query; save each raw page; return all results."""
    results, cursor, page = [], "*", 0
    while cursor:
        url = f"{url_base}&per-page=200&cursor={quote(cursor, safe='')}&mailto={MAILTO}"
        data = fetch(url)
        fp = outdir / f"{tag}_{page:03d}.json.gz"
        with gzip.open(fp, "wt") as f:
            json.dump(data, f)
        results.extend(data.get("results", []))
        cursor = (data.get("meta") or {}).get("next_cursor")
        page += 1
        time.sleep(0.12)
    return results

per_work = {json.loads(l)["doi"]: json.loads(l) for l in open(DATA / "per_work.jsonl")}
top25 = json.load(open(DATA / "top25_verified.json"))

out = []
for rank, t in enumerate(top25, 1):
    doi = t["doi"]; ry = t["retraction_year"]
    wdir = RAW / doi.replace("/", "_")
    wdir.mkdir(exist_ok=True)
    zid = (per_work[doi].get("openalex_id") or "").replace("https://openalex.org/", "")
    hop1_file = wdir / "hop1_done.json"
    if hop1_file.exists():
        hop1 = json.load(open(hop1_file))
    else:
        hop1 = sweep(f"https://api.openalex.org/works?filter=cites:{zid},publication_year:>{ry}"
                     f"&select={SELECT1}", wdir, "hop1")
    # Flag notice-type citers (see docstring) and persist the flag in the
    # cache artifact so it carries forward to 08 and any later consumer.
    notice_dois = {(per_work[doi].get("retraction_doi") or "").lower()}
    notice_dois.update((u.get("doi") or "").lower()
                       for u in t.get("crossref_update_to", []) or []
                       if "retract" in (u.get("type") or "").lower())
    notice_dois.discard("")
    for h in hop1:
        h["is_notice"] = is_notice(h, notice_dois)
    json.dump(hop1, open(hop1_file, "w"))
    notices = [h for h in hop1 if h["is_notice"]]
    research = [h for h in hop1 if not h["is_notice"]]
    hop2_restricted, fallbacks = 0, 0
    for h in research:
        cby = {c["year"]: c["cited_by_count"] for c in h.get("counts_by_year", [])}
        if cby:
            hop2_restricted += sum(c for y, c in cby.items() if y > ry)
        else:
            hop2_restricted += h.get("cited_by_count") or 0
            fallbacks += 1
    hop1_sorted = sorted(research, key=lambda h: -(h.get("cited_by_count") or 0))
    top_h1 = hop1_sorted[0] if hop1_sorted else None
    synth1 = [h for h in research if is_synthesis(h)]
    # Hop-2 synthesis candidates: title.search-restricted sweeps over batches
    # of hop-1 ids. (First attempt used the general `search=` parameter, which
    # matches abstracts/full text and returns orders of magnitude more pages;
    # title.search restricts to titles — exactly the population the local
    # title test judges. Verified against a sample 2026-10-13: returned
    # titles all genuinely carry the signal phrases.)
    hop1_ids = [(h.get("id") or "").replace("https://openalex.org/", "") for h in research]
    hop1_id_set = set(hop1_ids)
    synth2 = {}
    for bi in range(0, len(hop1_ids), 50):
        batch = [i for i in hop1_ids[bi:bi + 50] if i]
        if not batch: continue
        for term in ("meta-analysis", "systematic review"):
            cands = sweep(
                f"https://api.openalex.org/works?filter=cites:{'|'.join(batch)},"
                f"title.search:{quote(term, safe='-')}"
                f"&select=id,doi,title,publication_year,cited_by_count",
                wdir, f"synth2_{bi}_{term.replace(' ', '_')}")
            for c in cands:
                if c["id"] not in hop1_id_set and TITLE_RE.search(c.get("title") or "") \
                        and not is_notice(c, notice_dois):
                    synth2[c["id"]] = c
    s_total = len(synth1) + len(synth2)
    rec = {
        "rank": rank, "doi": doi, "title": t["title"], "journal": t["journal"],
        "original_year": t["original_year"], "retraction_year": ry,
        "post_retraction_citations_countsbyyear": t["post_retraction_citations"],
        "hop1_count": len(research),
        "hop1_notices": len(notices),
        "hop1_notice_titles": [h.get("title") for h in notices],
        "hop2_citations": hop2_restricted,
        "hop2_basis": ("citations in years after the retraction year (hop-1 counts_by_year)"
                       if fallbacks == 0 else
                       f"citations in years after the retraction year where year data exists; "
                       f"{fallbacks} of {len(research)} hop-1 research works lacked counts_by_year and "
                       f"contribute their all-time cited_by_count"),
        "hop1_top": ({"title": top_h1.get("title"), "year": top_h1.get("publication_year"),
                      "cited_by": top_h1.get("cited_by_count")} if top_h1 else None),
        "synthesis_hits": s_total,
        "synthesis_hop1": len(synth1), "synthesis_hop2": len(synth2),
        "synthesis_titles": ([h.get("title") for h in synth1] +
                             [c.get("title") for c in synth2.values()]),
        "implication": (f"{len(synth1)} identifiable systematic reviews or meta-analyses cited this "
                        f"retracted work directly and rest partly on it as an input; they warrant "
                        f"re-examination." if synth1 else
                        "No systematic review or meta-analysis citing this retracted work directly "
                        "was identifiable by title/concept signals; the works that cited it remain "
                        "exposed to a retracted input and warrant re-examination."),
        "discrepancy": t["discrepancy"],
    }
    out.append(rec)
    print(f"#{rank} {doi}: hop1={rec['hop1_count']} hop2={hop2_restricted} "
          f"synth={s_total} (h1 {len(synth1)} + h2 {len(synth2)}) fallbacks={fallbacks}", flush=True)

with open(DATA / "downstream.json", "w") as f:
    json.dump(out, f, indent=2)
print("wrote data/downstream.json")
