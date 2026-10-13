#!/usr/bin/env python3
"""Census analysis, codebook v3.1. Pair label = strongest panel label over its contexts.
Rates over research papers (retraction notices set aside), cluster-bootstrap 95% CIs over retracted papers,
and a strict/lenient band for contexts where the three models did not agree.
usage: SANECITE_DATA=... analyze_census.py   -> $DATA/census_results.json, $DATA/census_rows.jsonl"""
import json, os, random, re, sys, collections
sys.path.insert(0, os.path.dirname(__file__)); import panel as P, classify as C
DATA = os.environ["SANECITE_DATA"]
RANK = {"aware": 3, "substantive": 2, "perfunctory": 1, "unclear": 0}
PRICE = {"typesafe/jev": 0.042e-6, "@cf/cloudflare/clef": 0.24e-6}   # $/input token (CF model pages, 2026-10-13)
NEURON = 0.011 / 1000                                                 # Workers AI $/neuron
L = collections.defaultdict(dict); cost = collections.Counter(); calls = collections.Counter()
for tag in ("jev", "clef", "gemma"):
    fn = f"{DATA}/stage3_{tag}.jsonl"
    if not os.path.exists(fn): continue
    for l in open(fn):
        try: r = json.loads(l)
        except Exception: continue
        calls[r["model"]] += 1
        cost[r["model"]] += PRICE.get(r["model"], 0) * (r.get("pt") or 0) + NEURON * (r.get("neurons") or 0)
        if r.get("label") and r.get("codebook") == C.CODEBOOK: L[(r["pair_id"], r["ctx"])][r["model"]] = r  # one codebook only
s2 = []
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: s2.append(json.loads(l))
    except Exception: pass
# Retraction Watch reason tags. "Administrative" = withdrawn with no fault found in the science
# (out of date, replaced by a corrected version, moved journal, a publisher's duplicate).
# Notice/process tags say nothing about the science, so they are ignored when grouping.
ADMIN = {"withdrawn as out of date", "retract and replace", "withdrawn to publish in different journal",
         "duplication of content through error by journal/publisher", "error by journal/publisher", "temporary removal"}
META = {"investigation by journal/publisher", "notice - limited or no information", "date of article and/or notice unknown",
        "upgrade/update of prior notice(s)", "notice - lack of", "notice - unable to access via current resources",
        "investigation by company/institution", "investigation by third party", "investigation by ori", "removed"}
def reason_group(s):
    tags = [t.strip(" +").lower() for t in (s or "").split(";") if t.strip(" +")]
    core = [t for t in tags if t not in META]
    if core and all(t in ADMIN for t in core): return "administrative (no fault found in the science)"
    j = " ".join(core)
    if re.search(r"fabricat|falsif|manipulat|paper mill|fake peer|misconduct|plagiar|duplicat|randomly generated|forged|ethical violation", j): return "misconduct, fabrication or duplication"
    if re.search(r"error|unreliable|concerns/issues about (data|results|image)|not reproducible|contamination", j): return "error or unreliable results"
    return "other or unstated"
def field(subj):
    m = re.findall(r"\((\w+)\)", subj or ""); return m[0] if m else "?"
rows, notices, incomplete = [], 0, 0
for rec in s2:
    if rec.get("status") != "ok": continue
    if rec.get("is_notice"): notices += 1; continue
    labs, routes, strict, lenient, sizes = [], [], [], [], []
    for i in range(len(rec["contexts"])):
        rows_i = L.get((rec["pair_id"], i), {})
        if P.GEMMA not in rows_i or P.CLEF not in rows_i: labs = None; break
        sizes.append(P.panel_size(rows_i))
        lab, route = P.combine(rows_i, " ".join(C.passage(rec, i)))
        labs.append(lab); routes.append(route)
        if route == "unanimous": strict.append(lab); lenient.append(lab)
        else:
            vs = [rows_i[m]["label"] for m in P.PANEL if m in rows_i]
            strict.append("aware" if lab == "aware" else "perfunctory" if "perfunctory" in vs else lab)
            lenient.append("aware" if lab == "aware" else "substantive" if "substantive" in vs else lab)
    if labs is None: incomplete += 1; continue
    top = lambda xs: max(xs, key=lambda x: RANK[x])
    y = (int(rec["citing_year"]) - int(rec["retraction_year"])) if str(rec.get("citing_year") or "").isdigit() else None
    rows.append({"pair_id": rec["pair_id"], "paper": rec["retracted_pmid"], "label": top(labs), "strict": top(strict), "lenient": top(lenient),
                 "panel_size": min(sizes), "route": "split" if "split" in routes else "majority" if "majority" in routes else "unanimous",
                 "ref_retracted": bool(rec.get("ref_entry_flags_retraction")), "doc_mentions_retract": bool(rec.get("doc_mentions_retract")),
                 "reason": reason_group(rec.get("reason")), "field": field(rec.get("subject")), "years_after": y,
                 "retraction_year": rec["retraction_year"], "citing_year": rec.get("citing_year"), "n_contexts": len(labs),
                 "where": [c.get("where", "text") for c in rec["contexts"]]})
judged_all = [r for r in rows if r["label"] != "unclear"]
ADMIN_G = "administrative (no fault found in the science)"
judged = [r for r in judged_all if r["reason"] != ADMIN_G]   # headline: retractions that say the work is unreliable or improper
def boot(rs, pred, B=400, seed=1):
    by = collections.defaultdict(list)
    for r in rs: by[r["paper"]].append(pred(r))
    keys = list(by); rnd = random.Random(seed); vals = []
    sums = {k: (sum(v), len(v)) for k, v in by.items()}
    for _ in range(B):
        a = b = 0
        for k in (rnd.choice(keys) for _ in keys): a += sums[k][0]; b += sums[k][1]
        vals.append(a / max(1, b))
    vals.sort(); return [round(vals[int(.025 * B)], 4), round(vals[int(.975 * B) - 1], 4)]
def stat(rs, pred):
    if not rs: return None
    return {"rate": round(sum(map(pred, rs)) / len(rs), 4), "ci95": boot(rs, pred), "n": len(rs), "papers": len({r["paper"] for r in rs})}
res = {"headline_scope": "retractions other than administrative ones (out of date, replaced, moved journal, publisher duplicate)",
       "administrative_pairs": sum(r["reason"] == ADMIN_G for r in judged_all),
       "substantive_administrative": None, "codebook": C.CODEBOOK, "panel": list(P.PANEL), "pairs_classified": len(rows), "judged": len(judged), "unclear": len(rows) - len(judged),
       "notices_set_aside": notices, "incomplete_pairs": incomplete, "retracted_papers": len({r["paper"] for r in rows}),
       "routes": dict(collections.Counter(r["route"] for r in rows)),
       "panel_sizes": dict(collections.Counter(r["panel_size"] for r in rows))}
for lab in ("aware", "substantive", "perfunctory"):
    res[lab] = stat(judged, lambda r, lab=lab: r["label"] == lab)
res["by_panel_size"] = {n: {lab: stat([r for r in judged if r["panel_size"] == n], lambda r, lab=lab: r["label"] == lab)
                            for lab in ("aware", "substantive")} for n in (2, 3)}
res["substantive_band"] = {"strict": stat(judged, lambda r: r["strict"] == "substantive"), "lenient": stat(judged, lambda r: r["lenient"] == "substantive"),
                           "note": "strict = a context the three models split on counts as substantive only if no model said perfunctory; lenient = if any said substantive"}
_adm = [r for r in judged_all if r["reason"] == ADMIN_G]
res["substantive_administrative"] = stat(_adm, lambda r: r["label"] == "substantive")
res["ref_list_says_retracted"] = stat(rows, lambda r: r["ref_retracted"])
rr = [r for r in judged if r["ref_retracted"]]
res["substantive_despite_ref_list_label"] = stat(rr, lambda r: r["label"] == "substantive")
papers = collections.defaultdict(list)
for r in judged: papers[r["paper"]].append(r)
res["papers_with_any_substantive"] = {"papers": len(papers), "with_substantive": sum(any(x["label"] == "substantive" for x in v) for v in papers.values())}
def breakdown(key, keyfn):
    g = collections.defaultdict(list)
    for r in judged:
        k = keyfn(r)
        if k is not None: g[k].append(r)
    res[key] = {k: {"substantive": stat(v, lambda r: r["label"] == "substantive"), "aware": stat(v, lambda r: r["label"] == "aware")} for k, v in sorted(g.items())}
breakdown("by_years_after", lambda r: None if r["years_after"] is None else "1-2" if r["years_after"] <= 2 else "3-5" if r["years_after"] <= 5 else "6-10" if r["years_after"] <= 10 else "11+")
breakdown("by_reason", lambda r: r["reason"])
_j = judged; judged = judged_all; breakdown("by_reason_all", lambda r: r["reason"]); judged = _j
breakdown("by_citing_year", lambda r: None if not str(r["citing_year"] or "").isdigit() else str(min(int(r["citing_year"]), 2026)))
breakdown("by_retraction_decade", lambda r: f"{int(r['retraction_year']) // 10 * 10}s")
breakdown("by_field", lambda r: r["field"])
st = collections.Counter(r.get("status") for r in s2)
res["extraction"] = {"pairs": len(s2), "status": dict(st), "usable_rate": round(st["ok"] / max(1, len(s2)), 4)}
res["cost_usd"] = {m: round(v, 2) for m, v in cost.items()}; res["cost_usd"]["total"] = round(sum(cost.values()), 2); res["calls"] = dict(calls)
res["human_review_queue"] = {"pairs_not_unanimous": sum(r["route"] != "unanimous" for r in rows),
                             "substantive_or_aware_not_unanimous": sum(r["route"] != "unanimous" and r["label"] in ("substantive", "aware") for r in rows)}
# Misclassification correction (Rogan-Gladen) from the clean blind confirmation set (frozen v3.3):
# observed = sens*t + fpr*(1-t)  ->  t = (observed - fpr) / (sens - fpr)
try:
    cf = json.load(open(f"{DATA}/confirm_v33_score.json"))["confusion_gold_to_panel"]
    tp = cf.get("substantive->substantive", 0); fn = sum(v for k, v in cf.items() if k.startswith("substantive->") and not k.endswith("->substantive"))
    fp = sum(v for k, v in cf.items() if k.endswith("->substantive") and not k.startswith("substantive->"))
    tn = sum(v for k, v in cf.items() if not k.startswith("substantive->") and not k.endswith("->substantive"))
    sens, fpr = tp / (tp + fn), fp / (fp + tn)
    o = res["substantive"]["rate"]
    res["substantive_corrected"] = {"rate": round((o - fpr) / (sens - fpr), 4), "sens": round(sens, 4), "fpr": round(fpr, 4),
                                    "basis": "confirm_v33 blind set, n=" + str(tp + fn + fp + tn)}
except FileNotFoundError:
    pass
json.dump(res, open(f"{DATA}/census_results.json", "w"), indent=1)
with open(f"{DATA}/census_rows.jsonl", "w") as fo:
    for r in rows: fo.write(json.dumps(r) + "\n")
print(json.dumps({k: res.get(k) for k in ("substantive_corrected", "pairs_classified", "retracted_papers", "routes", "aware", "substantive", "substantive_band", "papers_with_any_substantive", "cost_usd")}, indent=1))
