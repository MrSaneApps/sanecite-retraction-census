#!/usr/bin/env python3
"""The /saez-zucman-check page (9 Nov 2026): fills the <!--sz:...--> markers in
tools/pages/saez-zucman-check.body.html from data/sz-check/verdicts.json.

verdicts.json is built in the S-Z check project (build_report.py, with the 9 Nov conformance overrides) and copied
here unchanged, with the PDF it matches. Every count on the page is recomputed from the 147 rows and must equal the
file's own totals, or the build stops; no figure on the page is typed by hand.

Markers: <!--sz:stats-->, <!--sz:cards-->, <!--sz:table-->, <!--sz:sp_table--> (blocks) and <!--sz:<key>--> (one value).
The second pass (9 Nov 2026) is checked the same way: its grade counts and 95% ranges are recomputed from its per-flag
grades and must match the file's totals and each flag's second_pass_grade."""
import collections, html, json, math, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = f"{ROOT}/data/sz-check/verdicts.json"
# Same rule as the project's build_report.py: the citation carries volume and page numbers, and is not a book reprint.
JOURNAL_RULE = re.compile(r"\b\d+(?:\(\d+\))?(?:-\d+)*:\s*\d+-\d+")
AT_TIME, LATER = "material available at the time", "data released later"


def stop(msg):
    raise SystemExit(f"build: saez-zucman-check: {msg}")


def and_list(rs):
    rs = [str(r) for r in rs]
    return ", ".join(rs[:-1]) + " and " + rs[-1] if len(rs) > 1 else "".join(rs)


def wilson(k, n, z=1.96):
    p, d = k / n, 1 + z * z / n
    c, h = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * (c - h) / d, 1), round(100 * (c + h) / d, 1)


def text(s):
    """Our notes as page text: escaped, curly apostrophes, and words quoted from a work in <q> (house rule)."""
    s = html.escape(s, quote=False)
    s = re.sub(r"(?<![\w’'])'([^']+?)'(?![\w])", r"<q>\1</q>", s)
    return s.replace("'", "’")


def load():
    d = json.load(open(DATA))
    f = d["flags"]
    if sorted(x["rank"] for x in f) != list(range(1, 148)):
        stop("verdicts.json must hold ranks 1 to 147 once each")
    T = d["totals"]
    facts = collections.Counter(x["facts"] for x in f)
    head = collections.Counter(x["headline_number"] for x in f)
    yes = [x for x in f if x["headline_number"] == "changes"]
    ranks = [x["rank"] for x in yes]
    journals = [x["rank"] for x in yes if JOURNAL_RULE.search(x["citation"]) and "(eds.)" not in x["citation"]]
    sample = [x for x in f if x["in_random_30"]]
    k30 = sum(x["headline_number"] == "changes" for x in sample)
    moved = T["moved_before_publishing"]
    added = T.get("added_after_reply_window", [])
    SP = d["second_pass"]
    spg = {g["rank"]: g["grade"] for g in SP["grades"]}
    sp_count = collections.Counter(spg.values())
    sp_tot = SP["totals"]["grades"]
    checks = {
        "facts": (dict(facts), {k: v for k, v in T["facts"].items() if v}),
        "headline_number": (dict(head), {k: v for k, v in T["headline_number"].items() if v}),
        "changes_ranks": (ranks, T["changes_ranks"]),
        "changes_at_time": (sum(x["shown_with"] == AT_TIME for x in yes), T["changes_at_time"]),
        "changes_later_data": (sum(x["shown_with"] == LATER for x in yes), T["changes_later_data"]),
        "no_change_claim_overstated": (sum(x["claim_overstated"] is True for x in f), T["no_change_claim_overstated"]),
        "journal_article_ranks": (journals, T["journal_article_ranks"]),
        "random_30": ((len(sample), k30), (30, T["random_30_changes"])),
        "random_30_range_95": (list(wilson(k30, 30)), T["random_30_range_95"]),
        "changes_in_copy_sent_29_oct": (len(yes) - len(added) + sum(m[1] == "YES" for m in moved), T["changes_in_copy_sent_29_oct"]),
        "added ranks change a headline number": (all(a[0] in ranks for a in added), True),
        "added ranks carry the dated note": (sorted(x["rank"] for x in f if x["added_note"]), sorted(a[0] for a in added)),
        "second pass grades": ({k: sp_count[k] for k in sp_tot}, {k: v["count"] for k, v in sp_tot.items()}),
        "second pass ranges": ({k: list(wilson(sp_count[k], len(spg))) for k in sp_tot}, {k: v["wilson95_pct"] for k, v in sp_tot.items()}),
        "second pass n": ((len(spg), sum(sp_count.values())), (SP["n"], SP["n"])),
        "second pass grade on each flag": ({x["rank"]: x["second_pass_grade"] for x in f if x["second_pass_grade"]}, spg),
        "second pass reclassified": (SP["totals"]["reclassified_to_changes"], [a[0] for a in added]),
        "every change has its work linked": (all(x["work_url"] for x in yes), True),
        "code flags change a headline number": (set(T["code_or_spreadsheet_ranks"]) <= set(ranks), True),
    }
    bad = [f"{k}: rows give {a}, totals say {b}" for k, (a, b) in checks.items() if a != b]
    if bad:
        stop("verdicts.json does not add up:\n  " + "\n  ".join(bad))
    lo, hi = wilson(k30, 30)
    vals = {
        "flags": len(f), "facts_right": facts["right"], "facts_partly": facts["partly right"],
        "facts_wrong": facts["wrong"], "facts_cannot": facts["could not check"],
        "changes": len(yes), "changes_pct": round(100 * len(yes) / len(f)),
        "changes_at_time": checks["changes_at_time"][0], "changes_later": checks["changes_later_data"][0],
        "disputed": head["depends on a disputed choice of method"], "no_change": head["does not change"],
        "overstated": checks["no_change_claim_overstated"][0], "cannot": head["could not check"],
        "code_n": len(T["code_or_spreadsheet_ranks"]), "code_list": and_list(T["code_or_spreadsheet_ranks"]),
        "journal_n": len(journals), "journal_list": and_list(journals),
        "random30_changes": k30, "random30_pct": round(100 * k30 / 30), "random30_lo": lo, "random30_hi": hi,
        "moved_n": len(moved), "moved_list": and_list([m[0] for m in moved]),
        "moved_disputed": and_list([m[0] for m in moved if m[2] == "JUDGEMENT CALL"]),
        "moved_no": and_list([m[0] for m in moved if m[2] == "NO"]),
        "sent_changes": checks["changes_in_copy_sent_29_oct"][0],
        "rev_defect": T["audit_revision_30_oct"]["defect"], "rev_contested": T["audit_revision_30_oct"]["contested choice"],
        "audit": d["audit"],
        "after_conf": len(yes) - len(added),
        "added_n": len(added), "added_links": and_list([f'<a href="#flag-{a[0]}">No. {a[0]}</a>' for a in added]),
        "sp_n": len(spg), "sp_agree": SP["totals"]["reader_agreement"]["count"],
        "sp_standard": sp_count["standard"], "sp_questionable": sp_count["questionable"],
        "sp_defensible": sp_count["defensible, stated in the paper"] + sp_count["defensible, not stated"],
        "sp_protocol": SP["files"]["protocol"], "sp_amendments": SP["files"]["amendments"],
        "sp_adjudication": SP["files"]["adjudication"], "sp_totals": SP["files"]["totals"],
    }
    vals["sp_tot"] = sp_tot
    return f, vals


def stats(v):
    rows = [(v["facts_right"], "facts all right", "Every fact in the flag that we could check was right."),
            (v["facts_wrong"], "core facts wrong", f"{v['facts_partly']} had smaller errors; {v['facts_cannot']} we could not check."),
            (v["changes"], "change a headline number", "Shown by a calculation or by the work’s own numbers."),
            (v["disputed"], "depend on a disputed choice of method", "Reasonable researchers differ on these. We take no side.")]
    return '<div class="szc-stats">' + "".join(
        f'<div class="proof"><span class="n">{n}<small> of {v["flags"]}</small></span><p><b>{html.escape(lab)}</b> {html.escape(sub)}</p></div>'
        for n, lab, sub in rows) + "</div>"


def cards(f):
    out = []
    for x in f:
        if x["headline_number"] != "changes":
            continue
        when = "shown at the time" if x["shown_with"] == AT_TIME else "shown by later data"
        out.append(
            f'<article class="card szc-card" id="flag-{x["rank"]}"><span class="eyebrow">No. {x["rank"]} · {when}</span>'
            f'<h3>{text(x["title"])}</h3><p class="szc-cite">{text(x["authors_short"])} · {text(x["citation"])}</p>'
            f'<p>{text(x["our_note"])}</p>'
            + (f'<p class="szc-cite"><b>{text(x["added_note"])}</b></p>' if x["added_note"] else "")
            +             f'<p class="szc-links"><a href="{html.escape(x["work_url"])}" rel="noopener">Read the work</a>'
            f' · <a href="{html.escape(x["audit_page"])}" rel="noopener">The audit’s page</a></p></article>')
    return '<div class="szc-cards">' + "".join(out) + "</div>"


def headline_words(x):
    h = x["headline_number"]
    if h == "changes":
        return "changes (shown at the time)" if x["shown_with"] == AT_TIME else "changes (shown by later data)"
    if h == "does not change" and x["claim_overstated"]:
        return "does not change; a claim is overstated in words"
    return h


def table(f):
    rows = []
    for x in f:
        note = f'<small>{text(x["our_note"])}</small>' if x["our_note"] else ""
        rows.append(f'<tr id="v-{x["rank"]}"><td>{x["rank"]}</td><td>{text(x["authors_short"])}, <q>{text(x["title"])}</q>{note}</td>'
                    f'<td data-l="Facts">{x["facts"]}</td><td data-l="Headline number">{headline_words(x)}</td>'
                    f'<td data-l="Second pass">{x["second_pass_grade"] or "not graded"}</td></tr>')
    return ('<div class="szc-tw"><table class="szc-t"><caption class="vh">Our verdict on each of the 147 flags</caption>'
            '<thead><tr><th scope="col">No.</th><th scope="col">Work and our note</th><th scope="col">Facts</th>'
            '<th scope="col">Headline number</th><th scope="col">Second pass</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def sp_table(v):
    rows = "".join(f'<tr><td>{html.escape(g[0].upper() + g[1:])}</td><td>{c["count"]}</td>'
                   f'<td style="white-space:nowrap">{c["wilson95_pct"][0]}-{c["wilson95_pct"][1]}%</td></tr>' for g, c in v["sp_tot"].items())
    return (f'<table class="cost" style="max-width:720px"><caption class="vh">Second-pass grades for the {v["sp_n"]} flags, with 95% ranges</caption>'
            f'<thead><tr><th scope="col" style="text-align:left">Grade</th><th scope="col" style="text-align:left">Flags</th>'
            f'<th scope="col" style="text-align:right">95% range</th></tr></thead><tbody>{rows}</tbody></table>')


def fill(body):
    if "<!--sz:" not in body:
        return body
    f, vals = load()
    blocks = {"stats": lambda: stats(vals), "cards": lambda: cards(f), "table": lambda: table(f), "sp_table": lambda: sp_table(vals)}

    def sub(m):
        k = m.group(1)
        if k in blocks:
            return blocks[k]()
        if k == "added_links":
            return vals[k]  # built from rank numbers only
        if k in vals and k != "sp_tot":
            return html.escape(str(vals[k]))
        stop(f"unknown marker <!--sz:{k}-->")
    return re.sub(r"<!--sz:([\w]+)-->", sub, body)
