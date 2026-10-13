#!/usr/bin/env python3
"""Planned analysis 6: compare the census with Hsiao and Schneider (QSS 2021; Illinois Data Bank IDB-3213475).
Their post-retraction citation contexts (PMC OA snapshot May 2019) carry a hand-checked "acknowledged the retraction"
judgement (724 contexts). On the (retracted PMID, citing PMCID) pairs both studies hold we report:
  A. extraction coverage: how many of their post-retraction pairs our pipeline found and read;
  B. agreement of our pair-level *aware* label with their acknowledgement (confusion, agreement, Cohen's kappa);
  C. both acknowledgement rates on the shared pairs.
usage: SANECITE_DATA=... hs_compare.py <hs_dir>  -> $SANECITE_DATA/hs_compare.json"""
import csv, io, json, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__)); import panel as P, classify as C
DATA, HS = os.environ["SANECITE_DATA"], sys.argv[1]

raw = open(f"{HS}/CitCntxt_withYR_v3.tsv", "rb").read().decode("cp1252", errors="replace")
raw = raw.replace("\r\n", "\n").replace("\r", "\n")
hs_post = {(r["intxt_pmid"], "PMC" + r["pmcid"]) for r in csv.DictReader(io.StringIO(raw), delimiter="\t")
           if r["post_retraction"] == "1"}
hs_ack = {(r["intxt_pmid"], "PMC" + r["pmcid"])
          for r in csv.DictReader(open(f"{HS}/724_knowingly_post_retraction_cit.csv", encoding="utf-8", errors="replace"))}

frame = {}
for l in open(f"{DATA}/stage1_papers.jsonl"):
    p = json.loads(l); frame[p["pmid"]] = {c["pmcid"] for c in p["oa_citers"]}
s2 = {}
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: r = json.loads(l)
    except Exception: continue
    s2[tuple(r["pair_id"].split(">"))] = r

in_frame = {k for k in hs_post if k[0] in frame}
cov = collections.Counter()
for k in in_frame:
    if k[1] not in frame[k[0]]: cov["not in our open-access citer list"] += 1
    elif k not in s2: cov["citer listed, pair not extracted"] += 1
    elif s2[k].get("is_notice"): cov["retraction notice (set aside)"] += 1
    elif s2[k]["status"] != "ok": cov["extraction: " + s2[k]["status"]] += 1
    else: cov["read"] += 1

shared = {k for k in in_frame if k in s2 and s2[k]["status"] == "ok" and not s2[k].get("is_notice")}
want = {"%s>%s" % k for k in shared}
L = collections.defaultdict(dict)
for tag in ("jev", "clef", "gemma"):
    fn = f"{DATA}/stage3_{tag}.jsonl"
    if not os.path.exists(fn): continue
    for l in open(fn):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("label") and r["pair_id"] in want: L[(r["pair_id"], r["ctx"])][r["model"]] = r

conf, sizes, skipped = collections.Counter(), collections.Counter(), 0
for k in shared:
    rec, labs = s2[k], []
    for i in range(len(rec["contexts"])):
        lab, _ = P.combine(L.get((rec["pair_id"], i), {}), " ".join(C.passage(rec, i)))
        if lab is None: labs = None; break
        labs.append(lab); sizes[P.panel_size(L[(rec["pair_id"], i)])] += 1
    if labs is None: skipped += 1; continue
    conf[("ack" if k in hs_ack else "no-ack", "aware" if "aware" in labs else "not-aware")] += 1

n = sum(conf.values()); a, b = conf[("ack", "aware")], conf[("ack", "not-aware")]
c, d = conf[("no-ack", "aware")], conf[("no-ack", "not-aware")]
po = (a + d) / n if n else None
pe = (((a + b) * (a + c) + (c + d) * (b + d)) / n ** 2) if n else None
res = {"source": "Hsiao & Schneider 2021, doi:10.13012/B2IDB-8255619_V2",
       "their_post_pairs": len(hs_post), "their_ack_pairs": len(hs_ack), "their_post_pairs_in_our_frame": len(in_frame),
       "coverage": dict(cov), "shared_pairs_read": len(shared), "shared_pairs_labelled": n, "skipped_incomplete": skipped,
       "panel_sizes_contexts": dict(sizes),
       "confusion": {"their_ack&our_aware": a, "their_ack&our_not": b, "their_no&our_aware": c, "their_no&our_not": d},
       "agreement": round(po, 4) if n else None, "kappa": round((po - pe) / (1 - pe), 4) if n and pe < 1 else None,
       "their_ack_rate_shared": round((a + b) / n, 4) if n else None, "our_aware_rate_shared": round((a + c) / n, 4) if n else None,
       "our_recall_of_their_ack": round(a / (a + b), 4) if a + b else None,
       "our_precision_vs_their_ack": round(a / (a + c), 4) if a + c else None}
json.dump(res, open(f"{DATA}/hs_compare.json", "w"), indent=1)
print(json.dumps(res, indent=1))
