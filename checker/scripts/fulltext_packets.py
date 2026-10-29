#!/usr/bin/env python3
"""Blind full-text re-read packets (feed check, 22 Oct 2026). Items: every reference "major" in b2-b5 plus a seeded
random draw of other reference citations (any label), shuffled together so a reader cannot tell which is which. Each
item shows the citing passage and the cited paper's full text (abstract, every body paragraph uncut, tables).
Readers never see the earlier labels.

Usage: fulltext_packets.py OUTDIR [--others 61] [--per 13] [--seed 1022]"""
import argparse, glob, json, os, random

D = os.path.expanduser("work/checker")


def refs(b):
    if b == "b5":
        g = {}
        for f in sorted(glob.glob(f"{D}/batches/b5/ref/ref-*.jsonl")):
            for l in open(f):
                r = json.loads(l); g[r["draw"]] = r["verdict"]
        return g
    return {r["draw"]: r["verdict"] for r in map(json.loads, open(f"{D}/batches/{b}/gold/gold.jsonl"))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--others", type=int, default=61)
    ap.add_argument("--per", type=int, default=13); ap.add_argument("--seed", type=int, default=1022)
    a = ap.parse_args()
    majors, rest, rows, full = [], [], {}, {}
    for b in ("b2", "b3", "b4", "b5"):
        for r in map(json.loads, open(f"{D}/batches/{b}/sample.jsonl")):
            if r.get("status") == "ok": rows[(b, r["draw"])] = r
        for x in map(json.loads, open(f"{D}/batches/{b}/fulltext.jsonl")):
            if x["status"] == "ok": full[(b, x["draw"])] = x
        for d, v in refs(b).items():
            if (b, d) in full: (majors if v == "major" else rest).append((b, d))
    rnd = random.Random(a.seed)
    pick = majors + rnd.sample(sorted(rest), a.others)
    rnd.shuffle(pick)
    os.makedirs(a.out, exist_ok=True)
    key = []
    for k in range(0, len(pick), a.per):
        with open(f"{a.out}/packet-{k // a.per + 1}.md", "w") as fh:
            for b, d in pick[k:k + a.per]:
                r, x = rows[(b, d)], full[(b, d)]
                c = r["context"]
                item = f"{b}-{d}"
                fh.write(f"## ITEM {item}\n\nCITING PASSAGE (section: {c.get('section') or 'unknown'}):\n")
                fh.write(f"{c.get('before', '')} {c['sentence']} {c.get('after', '')}\n\n")
                fh.write(f"CITED PAPER ({r.get('cited_year') or 'year unknown'}): {r['cited']['title']}\n\n")
                fh.write(f"ABSTRACT:\n{x['abstract']}\n\nFULL TEXT (every body paragraph, most related to the citing passage first):\n")
                for j, p in enumerate(x["paragraphs"]): fh.write(f"[P{j + 1}] {p}\n\n")
                for j, t in enumerate(x["tables"]): fh.write(f"[TABLE {j + 1}]\n{t}\n\n")
                fh.write("---\n\n")
                key.append({"item": item, "packet": k // a.per + 1})
    json.dump({"majors": len(majors), "others": a.others, "items": key}, open(f"{a.out}/key.json", "w"))
    print("majors", len(majors), "others", a.others, "packets", (len(pick) + a.per - 1) // a.per)


if __name__ == "__main__":
    main()
