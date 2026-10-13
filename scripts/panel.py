#!/usr/bin/env python3
"""Codebook v3.1 panel: combine per-model labels for one context.
Majority of jev, gemma and clef; 'aware' is decided separately because it is rare and costly to miss:
aware if a retraction/fraud word appears in the passage and ANY model says disputed, or if 2+ models say disputed.
Returns (label, route) where route = 'unanimous' | 'majority' | 'split'.
2026-10-13: jev ran out of paid credit after 44,248 census contexts. Contexts without a jev vote use the
two-model panel (gemma + clef); clef breaks ties (owner decision). panel_size() reports which panel judged."""
import collections, re
JEV, GEMMA, CLEF = "typesafe/jev", "@cf/google/gemma-4-26b-a4b-it", "@cf/cloudflare/clef"
PANEL = (JEV, GEMMA, CLEF)
AWARE_WORDS = re.compile(r"retract|withdrawn|fraud|fabricat|falsif|misconduct|plagiar|discredit|erroneous|flawed|expression of concern|not reproducib|irreproducib|could not be (?:replicated|reproduced)|appears? to overlap|overlaps? with (?:fig|figure|panel|image)|image (?:duplication|manipulation)|duplicated (?:image|panel|figure|blot)|manipulat(?:ed|ion) (?:image|figure|data|blot)", re.I)

def combine(rows, passage=""):
    """rows: {model: label-row dict with 'label' and 'stance'} for one context."""
    got = {m: r for m, r in rows.items() if r and r.get("label")}
    if CLEF not in got or len(got) < 2: return None, "missing"
    disputed = sum(r.get("stance") == "disputed" for r in got.values())
    if (AWARE_WORDS.search(passage or "") and disputed >= 1) or disputed >= 2:
        return "aware", "unanimous" if disputed == len(got) else "majority"
    labs = [got[m]["label"] if got[m]["label"] != "aware" else "substantive" for m in PANEL if m in got]
    c = collections.Counter(labs).most_common()
    if c[0][1] == len(labs): return c[0][0], "unanimous"
    if c[0][1] >= 2: return c[0][0], "majority"
    tie = got[JEV] if JEV in got else got[CLEF]
    return tie["label"] if tie["label"] != "aware" else "substantive", "split"

def panel_size(rows):
    return sum(1 for m in PANEL if (rows.get(m) or {}).get("label"))
