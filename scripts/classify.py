#!/usr/bin/env python3
"""Classify one citation context with a Cloudflare model.

Chat models go through clients/translations/scripts/llm_bakeoff.vendor_call
(researched per-model profiles + shared rate limits). typesafe/jev goes to the
shared /ai/run endpoint with a typed 'choice' question (schema in receipts/).
Labels follow CODEBOOK.md v1. The model never sees whether the paper was retracted."""
import json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.expanduser("~/SaneApps/clients/translations/scripts"))
from llm_bakeoff import vendor_call, DEFAULT_ACCOUNT  # noqa: E402

LABELS = ["aware", "substantive", "perfunctory", "unclear"]
CODEBOOK = "v3.3"
# v3 (2026-10-13): whether the target shares its citation group with other references is counted by code
# (citegroup.py), not judged by the model. The model answers two narrow questions; label() combines them.
STANCE = {
 "disputed": "Anywhere in the TEXT, including the sentences before and after the citation, or in the section heading, the target itself is called retracted, withdrawn, fraudulent, discredited, erroneous or flawed, its data are said to be confounded or unreliable, or its findings are said to have failed to replicate or not been confirmed by later studies. Plain disagreement is NOT disputed: 'our results differ from [→9]', 'in contrast to [→9]', or reporting that the target itself found no effect.",
 "neutral": "The text cites the target without saying anything against it.",
}
USE = {
 "specific": "The sentence rests on a finding of the target: a result, number, observation, or a method or protocol the authors took from it. Test: if the target's data had been made up, this sentence would lose its support. Includes 'X found that...', 'has been shown in mice [→7]', reported figures, 'as described in [→3]', 'consistent with [→9]', and one item in a list that carries the target alone.",
 "counted": "This paper is a review or meta-analysis and the target is one of the studies it includes and analyses as data: counted ('two of the eight included trials [→9,10]'), pooled, or a row in a table of included studies. NOT a general summary table of the literature, NOT 'in line with earlier meta-analyses', NOT 'most of the literature uses X'.",
 "background": "Textbook knowledge, a definition, a well-established mechanism, or a statement about a field, a need or an opinion. It would still stand if the target's data had been made up, even when only the target is cited.",
 "described": "It says what the target did, proposed or studied (a method it used, a hypothesis it put forward, that a topic has been researched) without resting on its result.",
 "unclear": "The text is garbled or too short to judge.",
}
EXAMPLES = """Examples (invented):
- "miR-195 suppresses tumours in liver [4] and in breast cancer [→5]." -> neutral, specific
- "Mice lacking VDR in muscle develop sarcopenia [→8]." -> neutral, specific
- "Our results agree with those of Lee et al. [→11]." -> neutral, specific
- "Cells were treated as described previously [→6]." -> neutral, specific
- "Inflammation drives many chronic diseases [→3]." -> neutral, background
- "Nrf2 regulates antioxidant genes such as HMOX1 and NQO1 [→2]." -> neutral, background
- "There is a need for cheaper diagnostic kits [→4]." -> neutral, background
- "Two explanations have been proposed: the heterogeneity and the individual-risk hypotheses [→5]." -> neutral, described
- "Smith et al. [→7] used a random forest to classify the images." -> neutral, described
- "Of the eight included trials, two enrolled only women [→9,10]." -> neutral, counted
- "Table of included studies: Iwamoto 2008 [→37] | Yonsei Med J | 12 months" -> neutral, counted
- "Our findings agree with earlier meta-analyses [5, →7]." -> neutral, specific
- "A later investigation found the data in [→8] were fabricated." -> disputed
- "Some data discussed in that review have since been retracted [→12]." -> disputed
- "Deleting ten toxin genes cut persister numbers [→14]. These data were later found to be confounded by phage contamination [15]." -> disputed
- "XMRV was detected in patients with chronic fatigue [→2]. Later studies failed to confirm any association [4–11]." -> disputed
- "Our findings are inconsistent with those of earlier studies [4, →9]." -> neutral, perfunctory use
- "A Cochrane review found no benefit of antivirals [→12]." -> neutral, specific"""
SYSTEM = ("You read how a scientific paper cites ONE target reference. The arrow → marks the in-text citation of the target.\n"
          "Answer two questions.\nstance:\n" + "\n".join(f"- {k}: {v}" for k, v in STANCE.items()) +
          "\nuse:\n" + "\n".join(f"- {k}: {v}" for k, v in USE.items()) + "\n" + EXAMPLES +
          '\nReply with JSON only, no prose: {"stance": "disputed|neutral", "use": "specific|counted|background|described|unclear", "quote": "<up to 20 words copied exactly from the TEXT that decided it>"}')

def group_n(rec, i=0):
    from citegroup import cite_group
    c = rec["contexts"][i]
    return cite_group(c["sentence"], c.get("where", "text"))[0]

COUNT_CUE = re.compile(r"\b(stud(y|ies)|trials?|RCTs?|included|pooled|meta-?analys[ie]s|systematic review|cohorts?|reviewed|articles|reports|participants|patients)\b", re.I)

def label(stance, use, n, text=""):
    """Codebook v3.1 decision rule. n = references sharing the target's citation group (None = unknown).
    'counted' needs a counting cue in the passage (studies, trials, included, pooled...), else it is treated as specific."""
    if re.search(r"\\documentclass|\\usepackage|\\begin\{", text or ""): return "unclear"  # formula markup, not prose
    if stance == "disputed": return "aware"
    if use == "counted" and (not text or COUNT_CUE.search(text)): return "substantive"
    if use == "counted": use = "specific"
    if n is not None and n >= 2: return "perfunctory"
    if use == "specific": return "substantive"
    if use == "unclear": return "unclear"
    return "perfunctory"

def passage(rec, i=0):
    c = rec["contexts"][i]
    return " ".join(x for x in (c["before"], c["sentence"], c["after"]) if x).strip(), c.get("section", "")

def group_note(n, item=False):
    if n is None: return "unknown"
    if n == 1: return "the target is cited alone" + ("; it backs one item of a list on its own" if item else "")
    return f"the target is cited together with {n - 1} other reference(s)"

def is_item(rec, i=0):
    from citegroup import list_item
    c = rec["contexts"][i]
    return list_item(c["sentence"], c.get("where", "text"))

def user_msg(rec, i=0):
    text, sec = passage(rec, i)
    where = rec["contexts"][i].get("where", "text")
    return (f"TARGET REFERENCE: {rec['retracted_title']}\nSECTION: {sec or 'n/a'}{' (table row)' if where == 'table' else ''}\n"
            f"CITATION GROUP: {group_note(group_n(rec, i), is_item(rec, i))}\nTEXT:\n{text}")

def parse(content):
    s = (content or "").strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.M).strip()
    m = re.search(r"\{.*\}", s, re.S)
    if not m: return None
    try: d = json.loads(m.group(0))
    except Exception:  # e.g. a stray quote inside "quote": keep the fields, drop the quote
        st = re.search(r'"stance"\s*:\s*"(\w+)"', s); us = re.search(r'"use"\s*:\s*"(\w+)"', s)
        if not us: return None
        d = {"stance": st.group(1) if st else "neutral", "use": us.group(1), "quote": ""}
    st, us = str(d.get("stance", "")).strip().lower(), str(d.get("use", "")).strip().lower()
    if us not in USE: return None
    return {"stance": st if st in STANCE else "neutral", "use": us, "quote": str(d.get("quote", ""))[:300]}

def norm(s): return re.sub(r"\W+", " ", (s or "").lower()).strip()

def quote_ok(quote, text):
    q = norm(quote)
    return bool(q) and q in norm(text)

def chat(model, rec, token, i=0):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg(rec, i)}]
    # SANECITE_MAX_TOKENS (amendment 2): larger reply cap, used only to retry the few replies cut off at the default.
    r = vendor_call(model, msgs, cf_token=token, account=DEFAULT_ACCOUNT, max_tokens=int(os.environ.get("SANECITE_MAX_TOKENS") or 0) or None)
    out = {"model": model, "ms": r.get("ms"), "neurons": r.get("neurons", 0), "pt": r.get("pt", 0), "ct": r.get("ct", 0)}
    if r.get("error"): out["error"] = str(r["error"])[:200]; return out
    p = parse(r.get("content"))
    if not p: out["error"] = "parse: " + str(r.get("content"))[:160]; return out
    n = group_n(rec, i)
    out.update(p); out.update({"group_n": n, "label": label(p["stance"], p["use"], n, " ".join(passage(rec, i))), "quote_ok": quote_ok(p["quote"], passage(rec, i)[0])})
    return out

def jev(rec, token=None, i=0, model="typesafe/jev"):
    """Typed 'choice' questions through the shared harness (jev_review.jev);
    model is typesafe/jev or Cloudflare's own @cf/cloudflare/clef."""
    import jev_review as jr
    text, sec = passage(rec, i)
    n = group_n(rec, i)
    state = {"target_reference": rec["retracted_title"], "section": sec or "n/a", "text": text,
             "location": rec["contexts"][i].get("where", "text"), "citation_group": group_note(n, is_item(rec, i)),
             "note": "The arrow \u2192 marks the in-text citation of the target reference."}
    q = {"stance": {"type": "choice", "instructions": "Read the whole text, including the sentences before and after the citation. Does it say anything against the target reference?", "criteria": STANCE},
         "use": {"type": "choice", "instructions": "How does the sentence use the target reference?\n" + EXAMPLES, "criteria": USE}}
    out, t0 = {"model": model}, time.time()
    for attempt in range(3):
        try:
            res = jr.jev(state, q, model=model); break
        except BaseException as e:  # jev() raises SystemExit when CF fails and no direct key
            res = None; out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            if "429" not in str(e) and "timed out" not in str(e): break
            time.sleep(5 * (attempt + 1))
    out["ms"] = int((time.time() - t0) * 1000)
    ans = (res or {}).get("answers") or {}
    st, us = ans.get("stance") or {}, ans.get("use") or {}
    if us.get("choice") not in USE: out.setdefault("error", "no answer: " + json.dumps(res)[:200]); return out
    out.pop("error", None)
    u = res.get("usage") or {}
    stance = st.get("choice") if st.get("choice") in STANCE else "neutral"
    out.update({"stance": stance, "use": us["choice"], "group_n": n, "label": label(stance, us["choice"], n, text + " " + (sec or "")),
                "confidence": us.get("confidence"), "stance_conf": st.get("confidence"), "probabilities": us.get("probabilities"),
                "pt": u.get("input_tokens", 0), "ct": u.get("output_tokens", 0), "version": res.get("model")})
    return out
