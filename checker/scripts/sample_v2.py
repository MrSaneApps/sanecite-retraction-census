#!/usr/bin/env python3
"""Stage 3 sampler v2 (batches of 1,000). Same population and pair rules as v1; changes: (1) random PMC IDs are
screened 100 at a time with one Europe PMC search (open access, 2015-2025) before any full text is fetched, which
keeps the simple random sample but skips dead IDs; (2) the cited-paper passages are chosen with the sentences before
and after the citation as well, and six passages are kept instead of five.

v1 notes: Stage 3 pilot sampler: random citations in PMC open-access papers whose cited paper is also open access.

Simple random sample of citing papers: draw PMC IDs uniformly from 1..MAX_PMCID (seeded), keep those Europe PMC
serves as open-access full text, published 2015-2025, research or review articles. From each kept paper draw ONE
reference with a PMID (seeded shuffle), keep the first whose cited paper is open-access full text in Europe PMC and
that is cited in the text, and take one random in-text citation of it. One pair per citing paper, so pairs are
independent. For the cited paper we keep the title, abstract and the five body paragraphs most similar to the
citing sentence (BM25), so a model can judge whether the citation is accurate.

Usage: sample_v2.py OUT.jsonl N --seed S [--workers 12]"""
import argparse, gzip, json, math, os, random, re, sys, threading, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.expanduser("work/census/protocol/scripts"))
import extract  # Campaign One's citation-context extractor (unchanged)

SEED = 20261021
MAX_PMCID = 13_683_000  # highest open-access PMCID seen in Europe PMC on 21 Oct 2026 was PMC13682390
YEARS = range(2015, 2026)
TYPES = {"research-article", "review-article"}
UA = {"User-Agent": "SaneCite-stage3-pilot (hi@saneapps.com)"}
REST = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def get(url, tries=3, timeout=60):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 500): return None  # Europe PMC answers 500 for a PMC id with no OA full text
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def xml_of(pmcid):
    b = get(f"{REST}/{pmcid}/fullTextXML")
    if not b: return None
    try: return extract.strip_ns(ET.fromstring(b)), b
    except ET.ParseError: return None


def year_of(root):
    for pd in root.iter("pub-date"):
        y = pd.find("year")
        if y is not None and (y.text or "").strip().isdigit(): return int(y.text.strip())
    return None


def article_type(root):
    art = root if root.tag == "article" else root.find(".//article")
    return ((art.get("article-type") if art is not None else "") or "").lower()


def meta(pmid):
    q = urllib.parse.urlencode({"query": f"EXT_ID:{pmid} AND SRC:MED", "format": "json", "resultType": "core", "pageSize": "1"})
    b = get(f"{REST}/search?{q}")
    if not b: return None
    res = json.loads(b).get("resultList", {}).get("result", [])
    return res[0] if res else None


TOK = re.compile(r"[a-z][a-z0-9\-]{2,}")
STOP = set("the and for with that this from were was are been have has had not but its into than then they their there these those which while when where also such can may using used use between within after before among our study studies results".split())


def toks(s): return [t for t in TOK.findall((s or "").lower()) if t not in STOP]


def bm25_top(paras, query, k=6):
    q = set(toks(query))
    if not paras or not q: return paras[:k]
    docs = [toks(p) for p in paras]
    n, avg = len(docs), sum(map(len, docs)) / max(1, len(docs))
    df = {t: sum(t in set(d) for d in docs) for t in q}
    def score(d):
        s, c = 0.0, {}
        for t in d: c[t] = c.get(t, 0) + 1
        for t in q:
            if t in c:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * c[t] * 2.2 / (c[t] + 1.2 * (0.25 + 0.75 * len(d) / max(1, avg)))
        return s
    best = sorted(range(n), key=lambda i: -score(docs[i]))[:k]
    return [paras[i] for i in sorted(best)]  # keep document order


def cited_excerpt(root, query):
    title = extract.text_of(root.find(".//article-title")) if root.find(".//article-title") is not None else ""
    ab = " ".join(extract.text_of(a) for a in root.iter("abstract"))[:3000]
    body = root.find(".//body")
    paras = [extract.text_of(p)[:1500] for p in (body.iter("p") if body is not None else []) if len(extract.text_of(p)) > 120]
    return {"title": title, "abstract": ab, "passages": bm25_top(paras, query), "n_paragraphs": len(paras)}


def refs_with_pmid(root):
    out = []
    for r in root.iter("ref"):
        pm = [p.text.strip() for p in r.iter("pub-id") if p.get("pub-id-type") == "pmid" and (p.text or "").strip().isdigit()]
        if pm:
            doi = next((p.text.strip() for p in r.iter("pub-id") if p.get("pub-id-type") == "doi" and p.text), "")
            t = r.find(".//article-title")
            out.append((pm[0], doi, extract.text_of(t) if t is not None else ""))
    return out


def try_paper(draw_index, pmcid, rng):
    log = {"draw": draw_index, "citing_pmcid": pmcid}
    got = xml_of(pmcid)
    if not got: return dict(log, status="no-oa-fulltext")
    root, raw = got
    y, at = year_of(root), article_type(root)
    if y not in YEARS: return dict(log, status="year-out", year=y)
    if at not in TYPES: return dict(log, status="type-out", article_type=at)
    refs = refs_with_pmid(root)
    if not refs: return dict(log, status="no-pmid-refs", year=y)
    rng.shuffle(refs)
    for pmid, doi, title in refs[:8]:
        m = meta(pmid)
        if not m or m.get("isOpenAccess") != "Y" or m.get("inEPMC") != "Y" or not m.get("pmcid") or m.get("pmcid") == pmcid:
            continue
        ctx = extract.contexts(raw, pmid, doi, title, max_ctx=5, year=None)
        if ctx.get("status") != "ok": continue
        cg = xml_of(m["pmcid"])
        if not cg: continue
        c = rng.choice(ctx["contexts"])
        query = " ".join([c.get("before", ""), c["sentence"], c.get("after", "")])
        jt = root.find(".//journal-title")
        types = [t.lower() for t in (m.get("pubTypeList") or {}).get("pubType", [])]
        return dict(log, status="ok", year=y, article_type=at, journal=extract.text_of(jt) if jt is not None else "",
                    n_refs_with_pmid=len(refs), cited_pmid=pmid, cited_pmcid=m["pmcid"], cited_year=m.get("pubYear"),
                    cited_journal=(m.get("journalInfo") or {}).get("journal", {}).get("title", ""),
                    cited_retracted=any("retract" in t for t in types), context=c,
                    n_contexts_of_cited=len(ctx["contexts"]), cited=cited_excerpt(cg[0], query))
    return dict(log, status="no-usable-oa-reference", year=y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("n", type=int)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--seed", type=int, required=True)
    a = ap.parse_args()
    global SEED
    SEED = a.seed
    done, kept = set(), 0
    if os.path.exists(a.out):
        for line in open(a.out):
            r = json.loads(line); done.add(r["draw"]); kept += r["status"] == "ok"
    master = random.Random(SEED)
    raw = [(i, f"PMC{master.randint(1, MAX_PMCID)}") for i in range(400_000)]

    def screened():  # one search per 100 draws; only open-access 2015-2025 IDs go on to the full-text fetch
        for k in range(0, len(raw), 100):
            if stop.is_set(): return
            chunk = [x for x in raw[k:k + 100] if x[0] not in done]
            if not chunk: continue
            q = "(" + " OR ".join(f"PMCID:{p}" for _, p in chunk) + ") AND OPEN_ACCESS:Y AND PUB_YEAR:[2015 TO 2025]"
            b = get(f"{REST}/search?" + urllib.parse.urlencode({"query": q, "format": "json", "pageSize": "100", "resultType": "idlist"}))
            ok = {r.get("pmcid") for r in (json.loads(b).get("resultList", {}).get("result", []) if b else [])}
            for i, p in chunk:
                if p in ok: yield (i, p)
                else:
                    with lock:
                        with open(a.out, "a") as fh: fh.write(json.dumps({"draw": i, "citing_pmcid": p, "status": "screened-out"}) + "\n")
                        seen["tried"] += 1
    lock, stop = threading.Lock(), threading.Event()
    draws = None
    seen = {"tried": len(done), "kept": kept, "t0": time.time()}

    def work(item):
        i, pmcid = item
        if stop.is_set() or i in done: return
        r = try_paper(i, pmcid, random.Random(SEED * 1_000_003 + i))
        with lock:
            if stop.is_set(): return
            with open(a.out, "a") as fh: fh.write(json.dumps(r) + "\n")
            seen["tried"] += 1; seen["kept"] += r["status"] == "ok"
            if seen["tried"] % 50 == 0:
                print(f"{time.strftime('%H:%M:%S')} STAGE sample tried={seen['tried']} kept={seen['kept']} "
                      f"rate={seen['kept'] / max(1, seen['tried']):.3f}", flush=True)
            if seen["kept"] >= a.n: stop.set()

    with ThreadPoolExecutor(a.workers) as ex:
        for _ in ex.map(work, screened()): pass
    print(f"{time.strftime('%H:%M:%S')} DONE sample tried={seen['tried']} kept={seen['kept']}", flush=True)


if __name__ == "__main__":
    main()
