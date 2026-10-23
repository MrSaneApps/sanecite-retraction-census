#!/usr/bin/env python3
"""Census analysis, codebook v3.1. Pair label = strongest panel label over its contexts.
Rates over research papers (retraction notices set aside), cluster-bootstrap 95% CIs over retracted papers,
and a strict/lenient band for contexts where the three models did not agree.
usage: SANECITE_DATA=... analyze_census.py   -> $DATA/census_results.json, $DATA/census_rows.jsonl

Correction of 20 Oct 2026 (amendment 11, part 4): pairs on Retraction Watch records whose PubMed ID points to a
different paper are listed in errata/wrong_records.csv (scripts/frame_check.py). Every row carries wrong_record, and
census_results.json reports the census as published (all pairs) and, under "corrected_wrong_records", without them."""
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
from groups import ADMIN_G, reason_group, field_group   # amendment 3: shared rules (groups.py)
import csv
WRONG_CSV = os.environ.get("SANECITE_WRONG_RECORDS") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "errata", "wrong_records.csv")
WRONG = set()
if os.path.exists(WRONG_CSV):
    for w in csv.DictReader(open(WRONG_CSV)): WRONG.update(w["affected_pair_ids"].split())
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
                 "reason": reason_group(rec.get("reason")), "field": field_group(rec.get("subject")), "field_codes": sorted(set(re.findall(r"\((\w+)\)", rec.get("subject") or ""))), "years_after": y,
                 "retraction_year": rec["retraction_year"], "citing_year": rec.get("citing_year"), "n_contexts": len(labs),
                 "where": [c.get("where", "text") for c in rec["contexts"]], "wrong_record": rec["pair_id"] in WRONG})
judged_all = [r for r in rows if r["label"] != "unclear"]
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
    vals.sort(); return [round(vals[int(.025 * B)], 6), round(vals[int(.975 * B) - 1], 6)]   # 6 places: reports round once, from here
def stat(rs, pred):
    if not rs: return None
    k = sum(map(pred, rs))   # count kept so reports compute k/n exactly; rounding the 4-place rate again gave 40.8% for 40.749%
    return {"rate": round(k / len(rs), 4), "k": k, "ci95": boot(rs, pred), "n": len(rs), "papers": len({r["paper"] for r in rs})}
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
res["aware_despite_ref_list_label"] = stat(rr, lambda r: r["label"] == "aware")   # amendment 3: saved (was quoted, not stored)
# amendment 3 (protocol analysis 6): aware rate on Hsiao & Schneider's citing-year window (their data end in 2019/2020)
res["aware_hs_window_citing_le_2019"] = stat([r for r in judged if str(r["citing_year"] or "").isdigit() and int(r["citing_year"]) <= 2019],
                                             lambda r: r["label"] == "aware")
papers = collections.defaultdict(list)
for r in judged: papers[r["paper"]].append(r)
res["papers_with_any_substantive"] = {"papers": len(papers), "with_substantive": sum(any(x["label"] == "substantive" for x in v) for v in papers.values()),
                                     "with_two_or_more_substantive": sum(sum(x["label"] == "substantive" for x in v) >= 2 for v in papers.values()),
                                     "note": "papers = non-administrative retracted papers with at least one judged citation"}
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
    # CI (PROTOCOL.md): resample the confirmation set (sens, fpr) and draw the observed rate from its census
    # bootstrap CI (normal, sd = width / 3.92), 2000 draws.
    items = ["tp"] * tp + ["fn"] * fn + ["fp"] * fp + ["tn"] * tn
    lo, hi = res["substantive"]["ci95"]; rnd, draws = random.Random(11), []
    for _ in range(2000):
        k = collections.Counter(rnd.choice(items) for _ in items)
        s, f = k["tp"] / max(1, k["tp"] + k["fn"]), k["fp"] / max(1, k["fp"] + k["tn"])
        if s - f > 0: draws.append(min(1, max(0, (rnd.gauss(o, (hi - lo) / 3.92) - f) / (s - f))))
    draws.sort(); res["substantive_corrected"]["ci95"] = [round(draws[int(.025 * len(draws))], 4), round(draws[int(.975 * len(draws)) - 1], 4)]
except FileNotFoundError:
    pass
# Amendment 3: rescore the confirmation set from its saved blind labels (reproduces confirm_v33_score.json) and repeat
# the correction with the headline's scope (administrative retractions out).
try:
    gold = {it["pair_id"]: it["pair"] for it in json.load(open(f"{DATA}/confirm_v33_gold.json"))["items"]}
    CL = collections.defaultdict(dict)
    for l in open(f"{DATA}/confirm_v33_labels.jsonl"):
        x = json.loads(l); CL[(x["pair_id"], x["ctx"])][x["model"]] = x
    cpanel, creason = {}, {}
    for l in open(f"{DATA}/confirm_v33.jsonl"):
        rec = json.loads(l); creason[rec["pair_id"]] = reason_group(rec.get("reason"))
        ls = [P.combine(CL.get((rec["pair_id"], i), {}), " ".join(C.passage(rec, i)))[0] for i in range(len(rec["contexts"]))]
        if ls and all(ls): cpanel[rec["pair_id"]] = max(ls, key=lambda x: RANK[x])
    def rg(keep):
        k = collections.Counter()
        for pid, g in gold.items():
            if pid not in cpanel or not keep(pid): continue
            k[("S" if g == "substantive" else "N") + ("S" if cpanel[pid] == "substantive" else "N")] += 1
        se, fp_ = k["SS"] / max(1, k["SS"] + k["SN"]), k["NS"] / max(1, k["NS"] + k["NN"])
        o = res["substantive"]["rate"]
        return {"n": sum(k.values()), "agree_substantive_or_not": k["SS"] + k["NN"], "sens": round(se, 4), "fpr": round(fp_, 4),
                "rate": round((o - fp_) / (se - fp_), 4)}
    res["substantive_corrected_rescored"] = {"all_150": rg(lambda pid: True), "non_administrative": rg(lambda pid: creason[pid] != ADMIN_G),
                                             "panel_differs_from_census_label": sorted(pid for pid in cpanel if pid in {r["pair_id"] for r in rows}
                                                                                       and cpanel[pid] != next(r["label"] for r in rows if r["pair_id"] == pid))}
except FileNotFoundError:
    pass
# Correction of 20 Oct 2026: the same figures without pairs on wrong records (errata/wrong_records.csv). The figures
# above stay as published; this block is the correction of record.
if WRONG:
    ok = [r for r in rows if not r["wrong_record"]]
    oj = [r for r in ok if r["label"] != "unclear" and r["reason"] != ADMIN_G]
    res["corrected_wrong_records"] = {
        "source": "errata/wrong_records.csv (amendment 11, part 4)", "pairs_removed": len(rows) - len(ok),
        "judged_removed": len(judged) - len(oj), "pairs_classified": len(ok), "judged": len(oj),
        "retracted_papers": len({r["paper"] for r in ok}),
        "substantive": stat(oj, lambda r: r["label"] == "substantive"), "aware": stat(oj, lambda r: r["label"] == "aware"),
        "perfunctory": stat(oj, lambda r: r["label"] == "perfunctory")}
res["cost_usd_note"] = ("logged usage at list prices; Jev's AI Gateway billing record for 13-14 Oct 2026 is $1.835 "
                        "(input tokens only, $0.042/M; fewer tokens billed than Jev reports per call)")
json.dump(res, open(f"{DATA}/census_results.json", "w"), indent=1)
with open(f"{DATA}/census_rows.jsonl", "w") as fo:
    for r in rows: fo.write(json.dumps(r) + "\n")
print(json.dumps({k: res.get(k) for k in ("substantive_corrected", "pairs_classified", "retracted_papers", "routes", "aware", "substantive", "substantive_band", "papers_with_any_substantive", "cost_usd")}, indent=1))
