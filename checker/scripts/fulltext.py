#!/usr/bin/env python3
"""Full text of each cited paper for the feed check (owner, 22 Oct: "make sure it's not an issue with HOW you are
feeding them data"). The stage 3 excerpts are the title, the abstract cut at 3,000 characters and six BM25 paragraphs
cut at 1,500; 58% of citations have at least one cut passage and the median paper has 38 paragraphs. Here: every body
paragraph uncut, table captions and cells, superscripts as ^ and subscripts as _ (the excerpts printed 10^5 as 105).
Paragraphs are ordered BM25-best first (same query as sample_v2), so a reader or a model that truncates keeps the best.

Usage: fulltext.py BATCH [--workers 6]  -> batches/BATCH/fulltext.jsonl (resumable)"""
import argparse, gzip, json, os, re, sys, threading, time, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

D = os.path.expanduser("work/checker")
sys.path.insert(0, os.path.join(D, "scripts"))
import sample_v2  # noqa: E402  (bm25_top, same tokenizer)

BLOCK = {"title", "p", "label", "sec", "caption", "td", "th", "list-item"}
SKIP = {"tex-math", "math", "mml:math", "disp-formula-group", "xref", "fig", "supplementary-material"}


def strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag: el.tag = el.tag.split("}", 1)[1]
    return root


def txt(el):
    def walk(e):
        if isinstance(e.tag, str) and e.tag in SKIP:
            if e.tag == "xref" and e.text: yield e.text  # keep in-text reference numbers
            return
        pre = "^" if e.tag == "sup" else "_" if e.tag == "sub" else ""
        if e.text: yield pre + e.text
        for c in e:
            yield from walk(c)
            if isinstance(c.tag, str) and c.tag in BLOCK: yield " "  # "Background" + "Acute" ran together
            if c.tail: yield c.tail
    return re.sub(r"\s+", " ", "".join(walk(el))).strip()


def fetch(pmcid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return None


def build(r):
    raw = fetch(r["cited_pmcid"])
    if not raw:
        return {"draw": r["draw"], "status": "fetch_failed"}
    root = strip_ns(ET.fromstring(raw))
    body = root.find(".//body")
    paras = [txt(p) for p in (body.iter("p") if body is not None else [])]
    paras = [p for p in paras if len(p) > 40]
    tables = []
    for tw in (body.iter("table-wrap") if body is not None else []):
        cap = " ".join(txt(c) for c in tw.iter("caption"))
        rows = [" | ".join(txt(c) for c in tr if c.tag in ("td", "th")) for tr in tw.iter("tr")]
        tables.append((cap + "\n" + "\n".join(rows)).strip())
    c = r["context"]
    query = f"{c.get('before', '')} {c['sentence']} {c.get('after', '')}"
    ranked = sample_v2.bm25_top(paras, query, k=len(paras)) if paras else []
    ab = " ".join(txt(a) for a in root.iter("abstract"))
    return {"draw": r["draw"], "status": "ok", "cited_pmcid": r["cited_pmcid"], "abstract": ab, "paragraphs": ranked,
            "tables": tables, "n_chars": len(ab) + sum(map(len, paras)) + sum(map(len, tables))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("batch"); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    b = os.path.join(D, "batches", a.batch)
    keep = set(json.load(open(os.path.join(b, "draws_judgeable.json"))))
    rows = [r for r in map(json.loads, open(os.path.join(b, "sample.jsonl"))) if r.get("status") == "ok" and r["draw"] in keep]
    out = os.path.join(b, "fulltext.jsonl")
    done = {json.loads(l)["draw"] for l in open(out)} if os.path.exists(out) else set()
    lock = threading.Lock()

    def work(r):
        rec = build(r)
        with lock, open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
        return rec["status"]

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(work, [r for r in rows if r["draw"] not in done]))
    print(f"{time.strftime('%H:%M:%S')} DONE fulltext {a.batch} new={len(res)} ok={res.count('ok')} failed={len(res) - res.count('ok')}", flush=True)


if __name__ == "__main__":
    main()
