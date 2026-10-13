#!/usr/bin/env python3
"""Export the Phase 2 census for sanecite.com/data.html.
usage: SANECITE_DATA=... export_site_data.py <site repo>/data/phase2

Writes:
  papers.json          one row per retracted paper with a classified citation (the page's search index)
  c/<bucket>.json      every classified citation of the papers in that bucket (loaded when a paper opens)
  citations.csv        one row per citing paper, labels only (download)
  contexts-<n>.csv     the citing sentences, split so no file passes Cloudflare Pages' 25 MiB limit
  census.json          the results (copy of census_results.json)"""
import csv, json, os, re, shutil, sys, collections
sys.path.insert(0, os.path.dirname(__file__)); import panel as P, classify as C
DATA = os.environ["SANECITE_DATA"]; OUT = sys.argv[1]
LABELS = ["substantive", "perfunctory", "aware", "unclear"]  # index order used by data.js
ROUTES = ["unanimous", "majority", "split"]
REASONS = ["misconduct, fabrication or duplication", "error or unreliable results", "other or unstated", "administrative (no fault found in the science)"]
FIELDS = {"BLS": "Life sciences", "HSC": "Health sciences", "PHY": "Physical sciences", "ENV": "Environment",
          "SOC": "Social sciences", "HUM": "Humanities", "B/T": "Business and technology"}
RANK = {"aware": 3, "substantive": 2, "perfunctory": 1, "unclear": 0}
def bucket(pmid): return f"{int(pmid) % 256:02x}"
L = collections.defaultdict(dict)
for tag in ("jev", "clef", "gemma"):
    for l in open(f"{DATA}/stage3_{tag}.jsonl"):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("label") and r.get("codebook") == C.CODEBOOK: L[(r["pair_id"], r["ctx"])][r["model"]] = r  # one codebook only
rows = {json.loads(l)["pair_id"]: json.loads(l) for l in open(f"{DATA}/census_rows.jsonl")}
recs = {}
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: r = json.loads(l)
    except Exception: continue
    if r["pair_id"] in rows: recs[r["pair_id"]] = r
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(f"{OUT}/c")
papers, shards = {}, collections.defaultdict(lambda: collections.defaultdict(list))
cit_rows, ctx_rows = [], []
for pid, row in rows.items():
    rec = recs.get(pid)
    if not rec: continue
    pm = rec["retracted_pmid"]
    p = papers.setdefault(pm, {"pmid": pm, "t": rec["retracted_title"], "j": rec.get("retracted_journal") or "", "ry": rec["retraction_year"],
                               "r": REASONS.index(row["reason"]), "f": row["field"], "doi": rec.get("retracted_doi") or "",
                               "n": 0, "s": 0, "p": 0, "a": 0, "x": 0, "u": 0})
    p["n"] += 1; p[{"substantive": "s", "perfunctory": "p", "aware": "a", "unclear": "u"}[row["label"]]] += 1
    p["x"] += row["route"] != "unanimous"
    best = None  # the context that decided the pair label, shown first
    ctxs = []
    for i, c in enumerate(rec["contexts"]):
        lab, route = P.combine(L[(pid, i)], " ".join(C.passage(rec, i)))
        ctxs.append((lab, route, c))
        if best is None or RANK[lab] > RANK[ctxs[best][0]]: best = i
    order = [best] + [i for i in range(len(ctxs)) if i != best]
    shown = []
    for i in order:
        lab, route, c = ctxs[i]
        sent = c["sentence"] if len(c["sentence"]) <= 420 else c["sentence"][:420] + "…"
        shown.append([LABELS.index(lab), ROUTES.index(route), (c.get("section") or "")[:60], sent, c.get("where", "text") == "table"])
        ctx_rows.append([pid, i, lab, route, c.get("section") or "", c.get("where", "text"), c["before"], c["sentence"], c["after"]])
    shards[bucket(pm)][pm].append([rec["citing_pmcid"], rec.get("citing_year"), (rec.get("citing_journal") or "")[:80],
                                   LABELS.index(row["label"]), ROUTES.index(row["route"]), bool(row["ref_retracted"]), shown])
    cit_rows.append([pid, pm, rec.get("retracted_doi") or "", rec["retraction_year"], row["reason"], row["field"], rec["citing_pmcid"],
                     rec.get("citing_year"), rec.get("citing_journal") or "", row["label"], row["strict"], row["lenient"], row["route"],
                     row["ref_retracted"], row["n_contexts"]])
plist = sorted(papers.values(), key=lambda p: (-p["s"], -p["n"], p["pmid"]))
meta = json.load(open(f"{DATA}/census_results.json"))
json.dump({"labels": LABELS, "routes": ROUTES, "reasons": REASONS, "fields": FIELDS, "codebook": meta.get("codebook"),
           "papers": [[p["pmid"], p["t"], p["j"], p["ry"], p["r"], p["f"], p["doi"], p["n"], p["s"], p["p"], p["a"], p["x"], p["u"]] for p in plist]},
          open(f"{OUT}/papers.json", "w"), ensure_ascii=False, separators=(",", ":"))
for b, d in shards.items():
    json.dump(d, open(f"{OUT}/c/{b}.json", "w"), ensure_ascii=False, separators=(",", ":"))
with open(f"{OUT}/citations.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["pair_id", "retracted_pmid", "retracted_doi", "retraction_year", "retraction_reason", "field", "citing_pmcid",
                                   "citing_year", "citing_journal", "label", "label_strict", "label_lenient", "panel_route", "ref_list_says_retracted", "n_contexts"])
    w.writerows(cit_rows)
part, size, f, w = 0, 0, None, None  # contexts CSV parts, each under 22 MiB
for r in ctx_rows:
    if f is None or size > 22 * 2**20:
        if f: f.close()
        part += 1; size = 0; f = open(f"{OUT}/contexts-{part}.csv", "w", newline=""); w = csv.writer(f)
        w.writerow(["pair_id", "context", "label", "panel_route", "section", "where", "before", "sentence", "after"])
    w.writerow(r); size += sum(len(str(x)) for x in r) + 20
if f: f.close()
shutil.copy(f"{DATA}/census_results.json", f"{OUT}/census.json")
idx = json.load(open(f"{OUT}/papers.json")); idx["context_files"] = [f"contexts-{i}.csv" for i in range(1, part + 1)]
json.dump(idx, open(f"{OUT}/papers.json", "w"), ensure_ascii=False, separators=(",", ":"))
CB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CODEBOOK.md")
if os.path.exists(CB): shutil.copy(CB, f"{OUT}/codebook.md")
print(f"papers {len(plist)}, citations {len(cit_rows)}, contexts {len(ctx_rows)}, shards {len(shards)}, context files {part}")
