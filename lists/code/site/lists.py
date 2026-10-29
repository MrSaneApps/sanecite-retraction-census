"""The Lists page for build.py: the retracted papers, citing journals and citing authors with the most
citations of retracted work as support. The lists themselves come from data/phase2/lists.json (made by the
census lists script, after a second reading of every entry's citations); every count and every ranking is
recomputed here from citations.csv and retraction_status.csv, and any mismatch stops the build. Also writes
the list CSVs and the full, unchecked tables for download. Rates come from k/n and are rounded once.

data/phase2/list_corrections.json holds every correction made after the data was generated (dates and reasons
from the notices, citations made before a retraction, notes printed beside items). They are applied here, before
the recount, so a regeneration cannot undo one: each correction names the value it expects to find, and the
build stops if the data holds neither that value nor the corrected one.

Replies from the people named (list_corrections.json "replies") are printed beside their entries and written to
lists/replies.csv, all by one rule (the replies rule): a summary in our words, one short verbatim quote (the sentence that states
the writer's main point), and any statement the writer supplied for publication, printed as written. A reply with no
quote, a quote over 40 words, a printed field holding an email address or phone number, an entry the lists do not
hold, or entry_now counts that no longer match the entry, stops the build. Where each reply came from is kept in tools/reply_sources.json, which is never served."""
import calendar, csv, json, os, re
from collections import Counter, defaultdict

from charts import ADMIN, AS_OF, CENSUS, P2, PROVISIONAL, ROOT, ROWS, esc, n, pct, rt

L = json.load(open(f"{P2}/lists.json"))
FIX = json.load(open(f"{P2}/list_corrections.json"))
# A paper that rose into a place after the corrections is held (not named) until its authors have been written to and
# have had the same time to reply (SOP H2). Everything that names it stays in tools/held.json, which is never served,
# and is merged in here; check_published() stops the build if a held id reaches any published file.
HELD = json.load(open(f"{ROOT}/tools/held.json")) if os.path.exists(f"{ROOT}/tools/held.json") else {}
if "pending_entries" in FIX:
    raise SystemExit("lists: pending_entries belong in tools/held.json, not in the published list_corrections.json")
FIX["pending_entries"] = HELD.get("pending_entries", [])
FIX["relabel"] = FIX.get("relabel", []) + HELD.get("relabel", [])
for k in ("papers", "second_read"):
    FIX["full_read"][k] = FIX["full_read"].get(k, []) + HELD.get("full_read", {}).get(k, [])
PENDING = {x["entry"] for x in FIX["pending_entries"]}
# Letters: one row per entry we wrote to, made by tools/sync_letters.py from the send ledger (never served). The
# build stops if anyone named on the page has no delivered letter with a reply date on or before publication.
LETTERS = json.load(open(f"{ROOT}/tools/letters.json"))
LETTER = {(x["list"], x["entry"]): x for x in LETTERS["entries"]}
ITEMS = json.load(open(f"{P2}/author_items.json"))
STATUS = {r["retracted_pmid"]: r for r in csv.DictReader(open(f"{P2}/retraction_status.csv", newline=""))}
RAW_CHECKS = list(csv.DictReader(open(f"{P2}/list_checks.csv", newline="")))
for x in FIX.get("check_notes", []):  # a reading note reworded, with the same old-or-new guard as every correction
    hit = [c for c in RAW_CHECKS if (c["list"], c["entry"], c["pair_id"]) == (x["list"], x["entry"], x["pair_id"])]
    if not hit or any(c["note"] not in (x["old"], x["new"]) for c in hit):
        raise SystemExit(f"lists: note correction {x[pair_id]} expects {x[old]!r} (or the corrected text) in list_checks.csv")
    for c in hit:
        c["note"] = x["new"]
LINKED = "retracted (linked)"
SUPPORT = "cited it as support"
MIN_J = L["journals_min_n"]
CENSUS_RATE = rt(CENSUS["substantive"])
CUT = L["cut"]
FAILS = []


def check(path, got, want):
    """Collects every mismatch, named by the lists.json field it concerns, so one build shows them all."""
    if got != want:
        FAILS.append({"path": path, "got": got, "want": want})


def stop(msg):
    raise SystemExit(f"lists: {msg}")


def day(iso):
    y, m, d = iso[:10].split("-")
    return f'{int(d)} {"Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(m) - 1]} {y}'


# ------------------------------------------------------------------ corrections to the generated data
def locate(path):
    """The dict and key a correction path names: papers/<pmid>/<field>, authors/<orcid>/<field>,
    journals/<by_count|by_rate>/<journal>/<field>, cited/<pmid>/<field>, or a top-level lists.json key."""
    k, *rest = path.split("/")
    if k == "cited":
        return ITEMS["cited"][rest[0]], rest[1]
    if k not in ("papers", "authors", "journals"):
        return L, k
    seq, key = (L["journals"][rest.pop(0)], "journal") if k == "journals" else (L[k], "pmid" if k == "papers" else "orcid")
    hit = [x for x in seq if x[key] == rest[0]]
    if not hit:
        if rest[0] in DROPPED:  # an entry the rules below take off the list needs no further corrections
            return None, None
        stop(f"correction {path}: no such entry")
    return hit[0], rest[1]


EXCLUDED = FIX["excluded_works"]  # retracted for reasons that do not touch the results: not counted anywhere
RELABEL = {x["pair_id"]: x for x in FIX.get("relabel", [])}
REMOVED = {f["path"] for f in FIX["fields"] if f.get("remove")}  # entries taken off the list by corrections  # labels corrected by an independent full-text check
DROPPED = set(EXCLUDED) | ({FIX["left_off_kept"]["pmid"]} if not FIX["left_off_kept"]["enabled"] else set())
for f in FIX["fields"]:
    if f.get("remove"):  # an entry that falls below the cut once the corrections are counted
        k, ident = f["path"].split("/")
        L[k] = [x for x in L[k] if x["orcid" if k == "authors" else "pmid"] != ident]
        continue
    obj, field = locate(f["path"])
    if obj is None:
        continue
    cur = obj.get(field)
    if cur == f["old"]:
        obj[field] = f["new"]
    elif cur != f["new"]:
        stop(f"correction {f['path']} expects {f['old']!r} (or the corrected {f['new']!r}) but the data holds {cur!r}")


for k in L["journals"]:  # corrected ranks can reorder a list; ties keep the generated order
    L["journals"][k].sort(key=lambda x: x["rank"])
L["authors"].sort(key=lambda x: x["rank"])
L["papers"].sort(key=lambda x: (x["rank"] is None, x["rank"] or 0))


def corrected_rows():
    """citations.csv with the notice dates applied (a citation counts only if made in a year after the retraction;
    in the retraction's own year, by the citing paper's first online date) and pre-retraction papers left out."""
    dates = {d["retracted_pmid"]: d for d in FIX["retraction_dates"]}
    drop = {p for x in FIX["exclude_citing"] for p in x["pairs"]}
    seen, edge, out, relabeled = set(), defaultdict(set), [], set()
    for r in ROWS:
        if r["retracted_pmid"] in EXCLUDED:
            continue
        if r["pair_id"] in drop:
            seen.add(r["pair_id"])
            continue
        r = dict(r, retraction_year_rw=r["retraction_year"])
        x = RELABEL.get(r["pair_id"])
        if x:  # a label an independent check of the full text corrected (Gate 7 pass 2)
            if r["label"] not in (x["old"], x["new"]):
                stop(f"relabel {r['pair_id']} expects label {x['old']} but citations.csv has {r['label']}")
            relabeled.add(r["pair_id"])
            r["label"] = x["new"]
        d = dates.get(r["retracted_pmid"])
        if d:
            if r["retraction_year"] not in (d["old"], d["new"]):
                stop(f"date correction {d['retracted_pmid']} expects year {d['old']} but citations.csv has {r['retraction_year']}")
            y, cy = int(d["new"]), int(r["citing_year"])
            if cy == y:
                edge[d["retracted_pmid"]].add(r["citing_pmcid"])
                if r["citing_pmcid"] not in d["boundary_keep"] + d["boundary_drop"]:
                    stop(f"date correction {d['retracted_pmid']}: {r['citing_pmcid']} is from {y} and is in neither boundary list")
            if cy < y or r["citing_pmcid"] in d["boundary_drop"]:
                continue
            r["retraction_year"] = d["new"]
        out.append(r)
    if drop - seen:
        stop(f"excluded citations not in citations.csv: {sorted(drop - seen)}")
    if set(RELABEL) - relabeled - {p for p in RELABEL if p.split(">")[0] in EXCLUDED}:
        stop(f"relabelled citations not in citations.csv: {sorted(set(RELABEL) - relabeled)}")
    for d in FIX["retraction_dates"]:
        if d["retracted_pmid"] not in EXCLUDED and set(d["boundary_keep"] + d["boundary_drop"]) != edge[d["retracted_pmid"]]:
            stop(f"date correction {d['retracted_pmid']}: boundary lists do not match the {d['new']} citing papers")
    return out


def in_scope(rows):
    """The lists' scope: judged citations (paperwork retractions and unclear labels left out) to papers PubMed links
    to a retraction notice. Replaced originals, records that are the replacement, and unconfirmed ones are left out."""
    return [r for r in rows if r["retraction_reason"] != ADMIN and r["label"] != "unclear"
            and STATUS.get(r["retracted_pmid"], {}).get("pubmed_status") == LINKED]


def excluded_rows():
    """Citations of the excluded works, kept out of every count but published with the notice's reason. The same
    date rules apply: citations made before the retraction are not among them."""
    dates = {d["retracted_pmid"]: d for d in FIX["retraction_dates"]}
    drop = {p for x in FIX["exclude_citing"] for p in x["pairs"]}
    out = []
    for r in ROWS:
        if r["retracted_pmid"] not in EXCLUDED or r["pair_id"] in drop:
            continue
        d = dates.get(r["retracted_pmid"])
        if d and (int(r["citing_year"]) < int(d["new"]) or r["citing_pmcid"] in d["boundary_drop"]):
            continue
        out.append(r)
    return out


J = in_scope(corrected_rows())
X = in_scope(excluded_rows())
ROW = {r["pair_id"]: r for r in J}
if {c["pair_id"] for c in RAW_CHECKS} - {r["pair_id"] for r in in_scope(ROWS)}:
    stop("list_checks.csv reads citations outside the lists' scope")
XCHK = {(x["list"], x["entry"], x["pair_id"]) for x in FIX["checks_exclude"]}
if XCHK - {(c["list"], c["entry"], c["pair_id"]) for c in RAW_CHECKS}:
    stop(f"excluded readings not in list_checks.csv: {sorted(XCHK - {(c['list'], c['entry'], c['pair_id']) for c in RAW_CHECKS})}")
# the second reading, limited to citations still in scope and without the readings taken out of the samples
CHECKS = [c for c in RAW_CHECKS if c["pair_id"] in ROW and (c["list"], c["entry"], c["pair_id"]) not in XCHK]
# A later full-text check (list_corrections.json "relabel") overrides the second reading for the same citation, so
# every confirmation counted below uses the final verdict, never a reading the full read reversed.
VERDICT = {"substantive": "cited it as support", "perfunctory": "mentioned it in passing",
           "aware": "flagged it as retracted or unreliable"}
for c in CHECKS:
    x = RELABEL.get(c["pair_id"])
    if x:
        c["final_verdict"] = VERDICT[x["new"]]
        c["reading_round"] = ("full read, two blind readings and a third reader" if x["source"].startswith("Two independent")
                              else "full read") + f' ({day(x["date"])})'
    else:
        c["final_verdict"], c["reading_round"] = c["second_reading"], "second reading"
STALE_SUPPORT = [c for c in CHECKS if c["second_reading"] == SUPPORT and c["final_verdict"] != SUPPORT]
RETRACTED_CITING = FIX["retracted_citing"]


def ranked(items, key):
    """Competition ranking (1, 2, 2, 4), cut at CUT with every tie at the cut kept."""
    out = []
    for i, x in enumerate(sorted(items, key=lambda x: -key(x))):
        r = out[-1][0] if out and key(x) == key(out[-1][1]) else i + 1
        if r > CUT: break
        out.append((r, x))
    return out


def check_ranks(prefix, entries, idkey, want):
    """Every listed entry's rank against the recount; an entry the recount drops below the cut is named."""
    want = {x if isinstance(x, str) else x[idkey]: r for r, x in want}
    have = {e[idkey] for e in entries}
    for e in entries:
        check(f"{prefix}/{e[idkey]}/rank", want.get(e[idkey], "below the cut"), e["rank"])
    held = {x["entry"] for x in FIX.get("pending_entries", []) if prefix.startswith(x["list"])}
    if set(want) - have - held:
        stop(f"{prefix}: the recount puts entries on the list that lists.json does not have: {sorted(set(want) - have - held)}")


def write_csv(name, header, rows):
    os.makedirs(f"{ROOT}/lists", exist_ok=True)
    with open(f"{ROOT}/lists/{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def reading(lst, entry):
    vs = [c for c in CHECKS if c["list"] == lst and c["entry"] == entry]
    return len(vs), sum(c["final_verdict"] == SUPPORT for c in vs)


def bar(v, top, text):
    return f'<span class="lb"><i style="--v:{v / top:.4f}"></i><b>{text}</b></span>'


# ------------------------------------------------------------------ papers
by_p = defaultdict(Counter)
for r in J: by_p[r["retracted_pmid"]][r["label"]] += 1
KEPT = FIX["left_off_kept"]
FULL_READ = FIX["full_read"]  # papers whose every "cited as support" citation was checked against the citing full text
# a paper whose retraction is not about the results is not listed at all; the switch off removes the kept paper
L["papers"] = [p for p in L["papers"] if p["pmid"] not in DROPPED]
listed = [p for p in L["papers"] if not p["left_off"]]
left = [p for p in L["papers"] if p["left_off"]]
for p in L["papers"]:
    c, k = by_p[p["pmid"]], f"papers/{p['pmid']}"
    check(f"{k}/support", c["substantive"], p["support"])
    check(f"{k}/judged", sum(c.values()), p["judged"])
    check(f"{k}/flagged", c["aware"], p["flagged"])
    r, cf = reading("paper", p["pmid"])
    check(f"{k}/read", r, p["read"])
    check(f"{k}/confirmed", cf, p["confirmed"])
off = {p["pmid"] for p in left}
check_ranks("papers", listed, "pmid", ranked([k for k in by_p if k not in off], lambda k: by_p[k]["substantive"]))
# every paper left off after reading ranks inside the cut on the count alone, so no unread paper was skipped.
# One exception, switched in list_corrections.json: a paper listed on a wrong date that we told the author we keep.
EXEMPT = {KEPT["pmid"]} if KEPT["enabled"] else set()
for p in left:
    inside = by_p[p["pmid"]]["substantive"] >= min(x["support"] for x in listed)
    check(f"papers/{p['pmid']}/left_off inside the cut", inside, p["pmid"] not in EXEMPT)
PAPER_SCOPE = len(by_p)
by_census = defaultdict(Counter)  # the same scope with no corrections applied: what the census labels alone give
for r in in_scope(ROWS):
    if r["retracted_pmid"] in by_p: by_census[r["retracted_pmid"]][r["label"]] += 1
CHANGED_PAPERS = sum(by_census[k] != c for k, c in by_p.items() if k not in PENDING)


def retracted_line(p):
    if p["reason"]:
        return f'Retracted {esc(p["retraction_year"])}: {esc(p["reason"])}.'
    return f'Retracted {esc(p["retraction_year"])}. We have not yet read the notice itself, so no reason is given here.'


def paper_cell(p):
    pub = f"{esc(p['first_author'])} et al., <i>{esc(p['journal'])}</i> {esc(p['year'])}"
    links = (f'<a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/" rel="noopener">paper</a> · '
             f'<a href="https://pubmed.ncbi.nlm.nih.gov/{p["notice_pmid"]}/" rel="noopener">retraction notice</a> · '
             f'<a href="/checker#{p["pmid"]}">every citation</a>')
    return (f'<td><span class="lt">{esc(p["title"])}</span><small>{pub}. {retracted_line(p)}</small>'
            + (f'<small class="lnote">{esc(p["note"])}</small>' if p["note"] else "")
            + f'<small>{links}</small>{reply_html("paper", p["pmid"])}</td>')


def held_rows(lst, cols):
    """A place an entry rose into after the corrections; it is named once its authors have been written to.
    Returned as (rank, row) so the table can sort them in beside the entries they tie with."""
    return [(x["rank"], f'<tr><td class="lr">{x["rank"]}</td><td colspan="{cols - 1}"><small>Held: a paper rose to this place '
                        f'after the {int(x["date"][8:])} October corrections. It will be named here once its authors have been '
                        f'written to and have had the same time to reply as everyone else.</small></td></tr>')
            for x in FIX.get("pending_entries", []) if x["list"] == lst]


def papers_table():
    top = max(p["support"] for p in listed)
    named = [(p["rank"],
              f'<tr><td class="lr">{p["rank"]}</td>{paper_cell(p)}'
              f'<td data-l="Cited as support">{bar(p["support"], top, n(p["support"]))}<small>of {n(p["judged"])} judged ({pct(p["support"] / p["judged"])})</small>'
              + ('<small>each one read twice</small>' if p["pmid"] in FULL_READ.get("second_read", []) else '') + '</td>'
              f'<td class="r" data-l="Second reading">{p["confirmed"]} of {p["read"]}<small>{"its questionnaire" if p["note"] else "its findings"}</small></td></tr>')
             for p in listed]
    rows = "".join(row for _, row in sorted(named + held_rows("papers", 4), key=lambda x: x[0]))  # stable: named first in a tie
    gone = "".join(
        f'<tr><td><span class="lt">{esc(p["title"])}</span><small>{esc(p["first_author"])} et al., '
        f'<i>{esc(p["journal"])}</i> {esc(p["year"])}. {retracted_line(p)}</small>'
        + (f'<small class="lnote">{esc(KEPT["footnote"])}</small>' if p["pmid"] in EXEMPT else "")
        + reply_html("paper", p["pmid"]) + f'</td><td class="r" data-l="Cited as support">{n(p["support"])}<small>of {n(p["judged"])}</small></td><td>{esc(p["left_off"])}</td></tr>'
        for p in sorted(left, key=lambda p: -p["support"]))
    rw = {r["retracted_pmid"]: (r["retraction_year_rw"], r["retraction_reason"]) for r in J}
    write_csv("papers", ["rank", "retracted_pmid", "title", "first_author", "journal", "year", "retraction_year_notice", "reason_notice",
                         "reason_source", "retraction_year_retraction_watch", "reason_group_retraction_watch", "retraction_notice_pmid",
                         "cited_as_support", "judged", "share_as_support", "flagged", "second_reading_read", "second_reading_confirmed",
                         "note", "left_off_because"],
              [[p["rank"] or "", p["pmid"], p["title"], p["first_author"], p["journal"], p["year"], p["retraction_year"],
                p["reason"] or "not yet read", p["reason_source"], *rw[p["pmid"]], p["notice_pmid"], p["support"], p["judged"],
                p["support"] / p["judged"], p["flagged"], p["read"], p["confirmed"],
                p["note"], p["left_off"] + (" " + KEPT["footnote"] if p["pmid"] in EXEMPT else "")] for p in listed + left])
    return (f'<div class="ltab"><table class="lst"><caption class="vh">The retracted papers most often still cited as support, ranked</caption>'
            f'<tr><th scope="col">#</th><th scope="col">Retracted paper</th><th scope="col">Cited as support after retraction</th>'
            f'<th scope="col" class="r">Second reading</th></tr>{rows}</table></div>'
            f'<p class="lfoot">Second reading: of up to 15 citations drawn at random and read again (fewer where a later full-text check took one out of scope), how many cite the paper as support, '
            f'and what they use it for. The sample was drawn before the full read; where the full read changed a citation\'s label, the final label is the one counted here and in '
            f'<a href="/lists/second-reading.csv" download>second-reading.csv</a>. Ties share a place. Each reason quotes or closely follows the retraction notice; where we '
            f'have not yet read a notice, we say so.</p><p class="lfoot">{esc(FULL_READ["note"])}</p>'
            f'<h3 class="lh3">Left off after reading</h3><p class="lfoot">These papers would make the list on the count alone, '
            f'but reading them showed the citations cite something the retraction does not touch, for example a tool or method '
            f'in the paper that still works.</p>'
            f'<div class="ltab"><table class="lst nr"><caption class="vh">Retracted papers left off after reading, with the reason</caption>'
            f'<tr><th scope="col">Retracted paper</th><th scope="col" class="r">Support</th><th scope="col">Why it is left off</th></tr>'
            f'{gone}</table></div>')


# ------------------------------------------------------------------ journals
by_j = defaultdict(Counter)
sup_by_j = defaultdict(set)
for r in J:
    by_j[r["citing_journal"]][r["label"]] += 1
    if r["label"] == "substantive": sup_by_j[r["citing_journal"]].add(r["citing_pmcid"])
J_TABLES = {"by_count": ("Most citations of retracted work as support", lambda j: by_j[j]["substantive"]),
            "by_rate": (f"Highest share as support, among journals with {MIN_J}+ judged citations",
                        lambda j: by_j[j]["substantive"] / sum(by_j[j].values()))}
eligible = [j for j in by_j if sum(by_j[j].values()) >= MIN_J]
check("journals_eligible", len(eligible), L["journals_eligible"])
for k, (_, key) in J_TABLES.items():
    check_ranks(f"journals/{k}", L["journals"][k], "journal", ranked(eligible if k == "by_rate" else list(by_j), key))
    for x in L["journals"][k]:
        c, p = by_j[x["journal"]], f"journals/{k}/{x['journal']}"
        check(f"{p}/support", c["substantive"], x["support"])
        check(f"{p}/judged", sum(c.values()), x["judged"])
        check(f"{p}/flagged", c["aware"], x["flagged"])
        check(f"{p}/papers_citing_as_support", len(sup_by_j[x["journal"]]), x["papers_citing_as_support"])
        r, cf = reading("journal", x["journal"])
        check(f"{p}/read", r, x["read"])
        check(f"{p}/confirmed", cf, x["confirmed"])


def sample_retracted(journal):
    return sorted({c["citing_pmcid"] for c in CHECKS if c["list"] == "journal" and c["entry"] == journal and c["citing_pmcid"] in RETRACTED_CITING})


def journals_table(k):
    lead, key = J_TABLES[k]
    js = L["journals"][k]
    top = max(key(x["journal"]) for x in js)

    def gone(x):
        s = sample_retracted(x["journal"])
        return (f'<small>{len(s)} of the papers read again {"has" if len(s) == 1 else "have"} since been retracted '
                f'({", ".join(s)})</small>') if s else ""
    rows = "".join(
        f'<tr><td class="lr">{x["rank"]}</td><td><span class="lt">{esc(x["journal"])}</span>'
        f'<small>{n(x["papers_citing_as_support"])} papers cite retracted work as support</small>{reply_html("journal", x["journal"])}</td>'
        f'<td data-l="{"Cited as support" if k == "by_count" else "Share cited as support"}">{bar(key(x["journal"]), top, n(x["support"]) if k == "by_count" else pct(x["support"] / x["judged"]))}'
        f'<small>{n(x["support"])} of {n(x["judged"])} judged ({pct(x["support"] / x["judged"])})</small></td>'
        f'<td class="r" data-l="Second reading">{x["confirmed"]} of {x["read"]}{gone(x)}</td></tr>' for x in js)
    return (f'<h3 class="lh3">{lead}</h3><div class="ltab"><table class="lst"><caption class="vh">Citing journals: {lead.lower()}</caption>'
            f'<tr><th scope="col">#</th><th scope="col">Citing journal</th>'
            f'<th scope="col">{"Cited as support" if k == "by_count" else "Share cited as support"}</th><th scope="col" class="r">Second reading</th></tr>'
            f'{rows}</table></div>')


def journals_block():
    for k in J_TABLES:
        write_csv(f"journals-{k.replace('_', '-')}", ["rank", "journal", "cited_as_support", "judged", "share_as_support", "flagged",
                                                     "papers_citing_as_support", "second_reading_read", "second_reading_confirmed"],
                  [[x["rank"], x["journal"], x["support"], x["judged"], x["support"] / x["judged"], x["flagged"],
                    x["papers_citing_as_support"], x["read"], x["confirmed"]] for x in L["journals"][k]])
    return (journals_table("by_count") + journals_table("by_rate") +
            f'<p class="lfoot">Second reading: 10 support citations per journal, drawn at random and read again; citations of work '
            f'retracted for a reason that does not touch the results were later taken out of the samples. Across the lists\' '
            f'scope, {pct(sum(c["substantive"] for c in by_j.values()) / len(J))} of citations are support (the census headline, '
            f'which also counts papers PubMed does not yet link to a notice, is {pct(CENSUS_RATE)}). With 100 to 300 citations, '
            f'a share can be off by several points either way, so close places in the second table are not real differences.</p>')


# ------------------------------------------------------------------ authors
sup_pmcs = {r["citing_pmcid"] for r in J if r["label"] == "substantive"}
A = L["authors"]
DEN = FIX["denominators"]["values"]
RCLASS = FIX["reason_class"]


def confirmed_pairs(a):
    g = f"{a['orcid']} {a['short']}"
    return sorted({c["pair_id"] for c in CHECKS if c["list"] == "author" and c["entry"] == g and c["final_verdict"] == SUPPORT})


for a in A:
    g, k = f"{a['orcid']} {a['short']}", f"authors/{a['orcid']}"
    pairs = confirmed_pairs(a)
    conf = sorted({p.split(">")[1] for p in pairs})
    check(f"{k}/papers_confirmed", conf, a["papers_confirmed"])
    r, cf = reading("author", g)
    check(f"{k}/citations_read", r, a["citations_read"])
    check(f"{k}/citations_confirmed", cf, a["citations_confirmed"])
    check(f"{k}/papers_found", [p for p in a["papers_found"] if p in sup_pmcs], a["papers_found"])
    check(f"{k}/retracted_cited", len({p.split(">")[0] for p in pairs}), a["retracted_cited"])
    check(f"{k}/reviews", sum(ITEMS["citing"][p]["review"] for p in conf), a["reviews"])
    for p in pairs:
        if p.split(">")[0] not in ITEMS["cited"] or p.split(">")[1] not in ITEMS["citing"]:
            stop(f"author_items.json has no display data for {p}")
        if p.split(">")[0] not in RCLASS:
            stop(f"list_corrections.json has no reason class for {p.split('>')[0]}")
    if a["orcid"] not in DEN:
        stop(f"no rate denominator for {a['short']}")
check_ranks("authors", A, "orcid", ranked(A, lambda a: len(a["papers_confirmed"])))
for a in A:
    mine = set(a["papers_confirmed"])
    want = [{"orcid": b["orcid"], "short": b["short"], "papers": len(mine & set(b["papers_confirmed"]))}
            for b in A if b is not a and len(mine & set(b["papers_confirmed"])) * 2 >= len(mine)]
    check(f"authors/{a['orcid']}/shares", want, a["shares"])
if FAILS:
    if os.environ.get("LISTS_MISMATCHES"):  # writes every mismatch as JSON, the starting point for a reviewed correction
        json.dump(FAILS, open(os.environ["LISTS_MISMATCHES"], "w"), indent=1)
    stop("these do not match lists.json after list_corrections.json:\n  " + "\n  ".join(f"{f['path']}: counted {f['got']!r}, lists.json {f['want']!r}" for f in FAILS))

TIMELINE = {(t["citing_pmcid"], t["retracted_pmid"]): t["text"] for t in FIX["timelines"]}

# ------------------------------------------------------------------ everyone named was written to (SOP B, C10, H2)
# The page says "Everyone named was written to before publication". This makes it a check, not a claim: every author,
# paper and journal the page names needs a delivered letter whose reply date falls on or before the publish date.
# A held entry stays held while its reply date is later. Journals in not_written are the page's stated exceptions.
NAMED = ({("authors", a["orcid"]) for a in A} | {("papers", p["pmid"]) for p in L["papers"]}
         | {("journals", x["journal"]) for k in L["journals"] for x in L["journals"][k]})
if PENDING & {e for _, e in NAMED}:
    stop(f"a held entry is named on the page: {sorted(PENDING & {e for _, e in NAMED})}")
if FIX["replies_deadline"] != LETTERS["default_reply_by"]:
    stop(f"list_corrections.json replies_deadline {FIX['replies_deadline']} differs from the letters' {LETTERS['default_reply_by']}")
EXCEPT = {("journals", x["journal"]) for x in FIX["not_written"]}
unwritten = sorted(f"{k} {e}" for k, e in NAMED - EXCEPT
                   if not (LETTER.get((k, e)) or {}).get("delivered") or not LETTER[(k, e)]["reply_by"]
                   or LETTER[(k, e)]["reply_by"] > LETTERS["publish_date"])
if unwritten:
    stop("named on the page without a delivered letter whose reply date is on or before "
         f"{LETTERS['publish_date']} (hold them in tools/held.json, or write first): {unwritten}")
for x in FIX["pending_entries"]:
    w = LETTER.get((x["list"], x["entry"]))
    if not w:
        stop(f"held entry {x['list']} {x['entry']} has no row in tools/letters.json")


# ------------------------------------------------------------------ replies from the people named
REPLIES = FIX["replies"]
SOURCES = json.load(open(f"{ROOT}/tools/reply_sources.json"))["replies"]  # private: never served, never written out
KINDS = ("author", "paper", "journal")
ON_PAGE = {"author": {a["orcid"]: a["name"] for a in A},
           "paper": {p["pmid"]: f'{p["first_author"]} et al., {p["journal"]} {p["year"]}' for p in L["papers"]},
           "journal": {x["journal"]: x["journal"] for k in L["journals"] for x in L["journals"][k]}}
TITLES = {p[0]: p[1] for p in json.load(open(f"{P2}/papers.json"))["papers"]}


def entry_counts(kind, key):
    if kind == "author":
        a = next(a for a in A if a["orcid"] == key)
        return {"papers": len(a["papers_confirmed"]), "citations": len(confirmed_pairs(a))}
    if kind == "paper":
        p = next(p for p in L["papers"] if p["pmid"] == key)
        return {"support": p["support"], "judged": p["judged"]}
    x = next(x for k in L["journals"] for x in L["journals"][k] if x["journal"] == key)
    return {"support": x["support"], "judged": x["judged"]}


def target(r):
    """The entry a reply belongs to, and whether that entry is on the page or only in the excluded-works data."""
    kinds = [k for k in KINDS if k in r]
    if len(kinds) != 1:
        stop(f"reply {r.get('id')}: name exactly one of author, paper or journal")
    kind, key = kinds[0], r[kinds[0]]
    if key in ON_PAGE[kind]:
        return kind, key, True
    if kind == "paper" and key in EXCLUDED:
        return kind, key, False
    if f"{kind}s/{key}" in REMOVED:  # an entry the corrections took off the list: the reply stays in the record
        return kind, key, False
    stop(f"reply {r['id']}: {kind} {key!r} is not on the lists or among the excluded works")


PRINTED = ("summary", "quote", "statement", "our_response", "changes")
REF_LABEL = "The published reference list marks the work as retracted"  # the heading over such items; replies must quote it exactly
# our words beside an entry never mention a human check or promise a later step (the one-letter rule; 23 Oct audit: a reply
# promised a named author the human check's findings for her entry)
# 23 Oct legal review: a printed response said we "will add the date if he sends it"; the old pattern missed "will add".
NO_PROMISE = re.compile(r"human (check|review|reader)|\b(we|I) will (send|check|read|review|share|tell|add|update|publish|print)"
                        r"|\bwe(?:'|’)ll\b|\bwill (add|send)\b|\bfund(ed|ing)?\b|expert reader", re.I)
# A summary reports the writer's words ("he says he will send the date"), so in it only our own promise counts.
OUR_PROMISE = re.compile(r"\bwe (will|shall)\b|\bwe(?:'|’)ll\b|\bwhen the human (check|review)", re.I)
# Text in quotation marks is the writer's, not ours: it is never checked for promises.
QUOTED = re.compile(r'"[^"]*"|“[^”]*”|<q>.*?</q>', re.S)


def promise_in(field, text):
    """The promise found in our words in a printed reply field, or None (the one-letter rule)."""
    ours = QUOTED.sub(" ", str(text))
    m = (NO_PROMISE if field in ("our_response", "changes") else OUR_PROMISE if field == "summary" else None)
    hit = m.search(ours) if m else None
    return hit.group(0) if hit else None


def reply_by(kind, key):
    """The reply date our letter to this entry stated (tools/letters.json); the build stops if there was no letter."""
    x = LETTER.get((kind + "s", key))
    if not x or not x["reply_by"]:
        stop(f"no delivered letter with a reply date for {kind} {key} in tools/letters.json")
    return x["reply_by"]


def reply_by_text():
    """'28 October', or the range of dates when letters gave different ones, from the entries named on the page."""
    dates = sorted({reply_by(k[:-1], e) for k, e in NAMED - EXCEPT})
    words = [f"{int(d[8:])} {calendar.month_name[int(d[5:7])]}" for d in dates]
    return words[0] if len(words) == 1 else "the date in each letter (" + ", ".join(words) + ")"
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d ()-]{8,}\d")  # an email address, or a phone-number-like digit run
for r in REPLIES:
    for f in ("id", "received", "from_role", "summary", "our_response"):
        if not str(r.get(f, "")).strip():
            stop(f"reply {r.get('id')}: {f} is empty")
    if not isinstance(r.get("changes"), list):
        stop(f"reply {r['id']}: changes must be a list (empty if nothing changed)")
    if not str(r.get("quote", "")).strip() and not r.get("summary_sent"):
        stop(f"reply {r['id']}: every reply gets one short verbatim quote (the replies rule); the quote is empty")
    if r.get("summary_sent") and r.get("quote"):
        stop(f"reply {r['id']}: summary_sent means the agreed summary is printed instead of a quote (the agreed-summary rule)")
    if r.get("quote") and len(r["quote"].split()) > 40:
        stop(f"reply {r['id']}: the quote is over 40 words")
    if "statement" in r and not (isinstance(r["statement"], str) and r["statement"].strip()):
        stop(f"reply {r['id']}: statement must be the writer's text, printed as written, or left out")
    for f in PRINTED:
        v = r.get(f, "")
        for text in (v if isinstance(v, list) else [v]):
            if CONTACT.search(str(text)):
                stop(f"reply {r['id']}: {f} holds an email address or phone number; remove contact details (the replies rule)")
    kind, key, shown = target(r)
    due = reply_by(kind, key)
    if (r["received"] > due) != bool(r.get("late")):
        stop(f"reply {r['id']}: received {r['received']}, reply date {due}: set late to {str(r['received'] > due).lower()}")
    for f in PRINTED:
        v = r.get(f, "")
        for text in (v if isinstance(v, list) else [v]):
            if promise_in(f, text):
                stop(f"reply {r['id']}: {f} mentions a human check or promises a later step (the one-letter rule): {promise_in(f, text)!r}")
            for q in re.findall(r'"([^"]*reference list[^"]*)"', str(text)):
                if q.lower() != REF_LABEL.lower():
                    stop(f"reply {r['id']}: {f} quotes the reference-list label as {q!r}, but the page prints {REF_LABEL!r}")
    if "entry_now" in r:
        if not shown:
            stop(f"reply {r['id']}: entry_now given for an entry that is not on the page")
        have = entry_counts(kind, key)
        if have != r["entry_now"]:
            stop(f"reply {r['id']}: says the entry is now {r['entry_now']}, the data holds {have}; update the reply")
ids = [r["id"] for r in REPLIES]
if len(set(ids)) != len(ids):
    stop("two replies share an id")
if set(ids) != set(SOURCES):
    stop(f"tools/reply_sources.json does not match the replies: missing {sorted(set(ids) - set(SOURCES))}, "
         f"extra {sorted(set(SOURCES) - set(ids))}")
for x in FIX["not_written"]:
    if x["journal"] not in ON_PAGE["journal"]:
        stop(f"not_written: {x['journal']} is not on the journal lists")
REPLY_AT = defaultdict(list)
for r in REPLIES:
    kind, key, shown = target(r)
    if shown:
        REPLY_AT[(kind, key)].append(r)


def reply_html(kind, key):
    return "".join(
        f'<div class="lreply" id="reply-{esc(r["id"])}"><span class="lrh">Reply from {esc(r["from_role"])}, received {day(r["received"])}'
        f'{", after the reply date" if r.get("late") else ""}</span>'
        f'<span>{esc(r["summary"])}</span>'
        + (f'<q>{esc(r["quote"])}</q>' if r.get("quote") else "")
        + (f'<span class="lrc2">Statement from {esc(r["from_role"])}, printed as written:</span><blockquote class="lrst">'
           + "".join(f"<p>{esc(p)}</p>" for p in r["statement"].split("\n\n")) + "</blockquote>" if r.get("statement") else "")
        + f'<span><b>Our response:</b> {esc(r["our_response"])}</span>'
        + (f'<span class="lrc2">Changes since our letter:</span><ul>{"".join(f"<li>{esc(c)}</li>" for c in r["changes"])}</ul>' if r["changes"] else "")
        + "</div>" for r in REPLY_AT[(kind, key)])


def replies_csv():
    out = []
    for r in REPLIES:
        kind, key, shown = target(r)
        name = ON_PAGE[kind].get(key) or TITLES.get(key, "")
        out.append([r["id"], kind, key, name, "on the page" if shown else "downloadable data only (excluded work)",
                    r["received"], reply_by(kind, key), "received after the reply date" if r.get("late") else "",
                    r["from_role"], r["summary"], r.get("quote", ""), r.get("statement", ""), r["our_response"],
                    " | ".join(r["changes"])])
    write_csv("replies", ["reply_id", "list", "entry_id", "entry", "shown", "received", "reply_by", "late", "from_role", "summary",
                          "quote", "statement", "our_response", "changes_since_letter"], out)


def replies_intro():
    left = "; ".join(f'{esc(x["journal"])} ({esc(x["why"])})' for x in FIX["not_written"])
    shown = sum(target(r)[2] for r in REPLIES)
    return (f'Everyone named was written to before publication{", except " + left if left else ""}. Replies received by '
            f'{reply_by_text()} are summarised and quoted beside their entries; statements written for publication are printed as written ({shown} on the page so far; '
            f'<a href="/lists/replies.csv" download>all replies</a>).')


def marked(pair):
    return ROW[pair]["ref_list_says_retracted"] == "True"


SHARDS = {}  # the checker's citation files (data/phase2/c/<bucket>.json), loaded once each


def in_checker(cited, citing):
    """True when the checker lists this citing paper under this retracted paper, so the passage link lands on it."""
    b = format(int(cited) % 256, "02x")  # the bucket rule in assets/data.js
    if b not in SHARDS:
        SHARDS[b] = json.load(open(f"{P2}/c/{b}.json"))
    return any(c[0] == citing for c in SHARDS[b].get(cited, []))


def cite_line(pair):
    cited, citing = pair.split(">")
    if not (re.fullmatch(r"\d+", cited) and re.fullmatch(r"PMC\d+", citing)):
        stop(f"{pair}: the passage link needs a numeric PMID and a PMC id (assets/data.js reads #<pmid>-<PMCID>)")
    if not in_checker(cited, citing):
        stop(f"{pair}: the checker does not list this citation, so its passage link would land on nothing")
    w, cls = ITEMS["cited"][cited], RCLASS[cited]
    if cls["class"] not in ("results", "unclear"):
        stop(f"{pair}: an excluded work is still counted")
    label = "Notice reason: results" if cls["class"] == "results" else f'Reason unclear ({esc(cls["why"])})'
    t = TIMELINE.get((citing, cited))
    return (f'<li>{esc(w["first_author"])} et al., <i>{esc(w["journal"])}</i>{" " + esc(w["year"]) if w["year"] else ""}, '
            f'{"retracted " if w["retraction_year"][:1].isdigit() else ""}{esc(w["retraction_year"])}. <span class="lrc">{label}</span> '
            f'<a class="lpass" href="/checker#{esc(cited)}-{esc(citing)}" aria-label="The passage: {esc(citing)} citing '
            f'{esc(w["first_author"])} et al.">See the passage</a>'
            + (f'<span class="ltl">{esc(t)}</span>' if t else "") + "</li>")


def paper_item(pmc, pairs):
    p = ITEMS["citing"][pmc]
    rc = RETRACTED_CITING.get(pmc)
    note = TIMELINE.get((pmc, ""))
    return (f'<li><a href="https://europepmc.org/article/PMC/{pmc}" rel="noopener">{esc(p["title"])}</a> '
            f'<span class="lmeta"><i>{esc(p["journal"])}</i> {esc(p["year"])}{" · review" if p["review"] else ""}</span>'
            + (f'<span class="lflag">This paper has itself been retracted ({esc(rc["when"])}).{" " + esc(rc["note"]) if rc["note"] else ""}</span>' if rc else "")
            + (f'<span class="ltl">{esc(note)}</span>' if note else "")
            + f'<ul>{"".join(cite_line(x) for x in pairs)}</ul></li>')


def author_items(a):
    pairs = confirmed_pairs(a)
    groups = []
    for want in (False, True):
        by = defaultdict(list)
        for x in pairs:
            if marked(x) == want: by[x.split(">")[1]].append(x)
        groups.append("".join(paper_item(pmc, by[pmc]) for pmc in sorted(by, key=lambda p: (ITEMS["citing"][p]["year"], p))))
    plain, flagged = groups
    return (f'<details class="litems"><summary>The {len(a["papers_confirmed"])} papers and {len(pairs)} citations</summary>'
            + (f'<ol>{plain}</ol>' if plain else "")
            + (f'<p class="lsub">{REF_LABEL}</p><ol>{flagged}</ol>' if flagged else "")
            + "</details>")


def item_rows():
    for a in A:
        for x in confirmed_pairs(a):
            cited, citing = x.split(">")
            w, p, cls, rc = ITEMS["cited"][cited], ITEMS["citing"][citing], RCLASS[cited], RETRACTED_CITING.get(citing)
            yield [a["name"], a["orcid"], citing, p["title"], p["journal"], p["year"], int(p["review"]), cited, w["first_author"],
                   w["journal"], w["year"], w["retraction_year"], cls["notice_pmid"], cls["class"], cls["why"], int(marked(x)),
                   TIMELINE.get((citing, cited)) or TIMELINE.get((citing, "")) or "",
                   f'retracted {rc["when"]} (notice PMID {rc["notice_pmid"]}) {rc["note"]}'.strip() if rc else ""]


def authors_table():
    top = max(len(a["papers_confirmed"]) for a in A)
    group = {a["orcid"] for a in A if a["shares"]}
    names = {a["orcid"]: a["name"] for a in A}

    def shares(a):
        if not a["shares"]: return ""
        return "<small>Co-wrote " + " and ".join(f'{s["papers"]} of them with {esc(names[s["orcid"]])}' for s in a["shares"]) + "</small>"

    rate = lambda a: len(a["papers_confirmed"]) / DEN[a["orcid"]]
    rows = "".join(
        f'<tr class="lhas"><td class="lr">{a["rank"]}</td><td><span class="lt">{esc(a["name"])}</span>'
        f'<small><a href="https://orcid.org/{a["orcid"]}" rel="noopener">ORCID {a["orcid"]}</a></small>{shares(a)}</td>'
        f'<td data-l="Papers citing as support">{bar(len(a["papers_confirmed"]), top, len(a["papers_confirmed"]))}<small>of {len(a["papers_found"])} found by the census</small></td>'
        f'<td class="r" data-l="Rate">{pct(rate(a))}<small>of {n(DEN[a["orcid"]])} tagged papers</small></td>'
        f'<td class="r" data-l="Reviews">{a["reviews"]}</td><td class="r" data-l="Retracted papers cited">{a["retracted_cited"]}</td></tr>'
        f'<tr class="lit"><td></td><td colspan="5">{author_items(a)}{reply_html("author", a["orcid"])}</td></tr>' for a in A)
    write_csv("authors", ["rank", "name", "orcid", "papers_confirmed", "papers_found", "orcid_tagged_oa_papers_2010_2026", "rate",
                          "reviews_among_confirmed", "retracted_papers_cited", "citations_read", "citations_confirmed", "confirmed_papers_pmcid"],
              [[a["rank"], a["name"], a["orcid"], len(a["papers_confirmed"]), len(a["papers_found"]), DEN[a["orcid"]], rate(a), a["reviews"],
                a["retracted_cited"], a["citations_read"], a["citations_confirmed"], ";".join(a["papers_confirmed"])] for a in A])
    write_csv("author-items", ["author", "orcid", "citing_pmcid", "citing_title", "citing_journal", "citing_year", "citing_is_review",
                               "retracted_pmid", "retracted_first_author", "retracted_journal", "retracted_year", "retraction_year",
                               "retraction_notice_pmid", "notice_reason_class", "notice_reason_note", "reference_list_shows_retraction",
                               "timeline", "citing_paper_retracted"], item_rows())
    n_items = sum(len(confirmed_pairs(a)) for a in A)
    n_marked = sum(marked(x) for a in A for x in confirmed_pairs(a))
    return (f'<div class="ltab"><table class="lst"><caption class="vh">The authors whose papers most often cite retracted work as support, ranked</caption>'
            f'<tr><th scope="col">#</th><th scope="col">Author</th><th scope="col">Papers citing retracted work as support</th>'
            f'<th scope="col" class="r">Rate</th><th scope="col" class="r">Reviews</th><th scope="col" class="r">Retracted papers cited</th></tr>{rows}</table></div>'
            f'<p class="lfoot">Papers: citing papers with at least one citation the second reading confirmed as support. '
            f'Rate: those papers as a share of the author\'s open-access papers in PMC that carry their ORCID iD in Europe PMC, '
            f'2010 to 2026 (counted {esc(FIX["denominators"]["counted"])}). The ranking stays by count. Below the top three, the order '
            f'does not hold under rates: authors with few tagged papers can have high rates on small numbers. '
            f'Reviews: how many of those papers Europe PMC lists as review articles. Every support citation in every listed '
            f'author\'s papers was read again ({n(sum(a["citations_read"] for a in A))} in all). The {len(group)} authors who share '
            f'papers wrote most of them together, so their counts overlap. Ties share a place.</p>'
            f'<p class="lfoot">Each listed item names the notice\'s reason. <b>Results</b>: the notice names a problem with the '
            f'data, images or results, or says they cannot be relied on. <b>Unclear</b>: it gives no reason or a vague one, or we have '
            f'not read it yet; these still count. Citations of work retracted only for reasons that do not touch the results are left '
            f'out, as the census leaves out paperwork retractions. '
            f'Where a citing paper was submitted or accepted before the retraction, its timeline is printed beside the item; '
            f'papers that went online before the retraction are left out. {n_marked} of the {n(n_items)} items sit apart: '
            f'the citing paper\'s published reference list marks the work as retracted. Such labels and links are often added '
            f'automatically during publication, so they do not show that the authors knew.</p>')


# ------------------------------------------------------------------ full tables, not read again
NOTICE = {d["retracted_pmid"]: (d["new"], "") for d in FIX["retraction_dates"]}
NOTICE.update({p["pmid"]: (p["retraction_year"], p["reason"] or "not yet read") for p in L["papers"]})


FULL_ROWS = {}  # rows written to all-papers.csv and all-journals.csv, filled by full_tables()


def full_tables():
    titles = {}
    for p in json.load(open(f"{P2}/papers.json"))["papers"]:
        titles[p[0]] = p[1]
    rw = {r["retracted_pmid"]: (r["retraction_year_rw"], r["retraction_reason"]) for r in J}
    paper_rows = [[k, titles.get(k, ""), *rw[k], *NOTICE.get(k, ("", "")), c["substantive"], c["perfunctory"], c["aware"], sum(c.values()),
                   c["substantive"] / sum(c.values()), by_census[k]["substantive"], sum(by_census[k].values())]
                  for k, c in sorted(by_p.items(), key=lambda x: (-x[1]["substantive"], x[0])) if k not in PENDING]
    journal_rows = [[j, c["substantive"], c["perfunctory"], c["aware"], sum(c.values()), c["substantive"] / sum(c.values())]
                    for j, c in sorted(by_j.items(), key=lambda x: (-x[1]["substantive"], x[0]))]
    write_csv("all-papers", ["retracted_pmid", "title", "retraction_year_retraction_watch", "reason_group_retraction_watch",
                             "retraction_year_notice", "reason_notice", "cited_as_support", "mentioned_in_passing", "flagged",
                             "judged", "share_as_support", "census_cited_as_support", "census_judged"], paper_rows)
    write_csv("all-journals", ["journal", "cited_as_support", "mentioned_in_passing", "flagged", "judged", "share_as_support"],
              journal_rows)
    FULL_ROWS.update(papers=len(paper_rows), journals=len(journal_rows))  # the counts the page states for these files
    by_x = defaultdict(Counter)
    for r in X: by_x[r["retracted_pmid"]][r["label"]] += 1
    write_csv("excluded-works", ["retracted_pmid", "title", "left_out_because", "notice_pmid", "notice_says", "cited_as_support",
                                 "mentioned_in_passing", "flagged", "judged"],
              [[k, titles.get(k, ""), "retracted for a reason that does not touch the results", EXCLUDED[k]["notice_pmid"],
                EXCLUDED[k]["notice_says"], c["substantive"], c["perfunctory"], c["aware"], sum(c.values())]
               for k, c in sorted(by_x.items(), key=lambda x: (-x[1]["substantive"], x[0]))])
    write_csv("excluded-citations", ["pair_id", "retracted_pmid", "left_out_because", "citing_pmcid", "citing_year", "citing_journal",
                                     "census_label", "ref_list_says_retracted"],
              [[r["pair_id"], r["retracted_pmid"], "retracted for a reason that does not touch the results", r["citing_pmcid"],
                r["citing_year"], r["citing_journal"], r["label"], r["ref_list_says_retracted"]]
               for r in sorted(X, key=lambda r: (r["retracted_pmid"], r["citing_pmcid"]))])
    write_csv("second-reading", ["list", "entry", "pair_id", "retracted_pmid", "citing_pmcid", "census_label", "second_reading", "note",
                                 "final_verdict", "reading_round", "citing_paper_retracted"],
              [[c[k] for k in ("list", "entry", "pair_id", "retracted_pmid", "citing_pmcid", "census_label", "second_reading", "note",
                               "final_verdict", "reading_round")]
               + [RETRACTED_CITING[c["citing_pmcid"]]["when"] if c["citing_pmcid"] in RETRACTED_CITING else ""] for c in CHECKS])
    check_final()
    replies_csv()
    on_lists_json()
    left = "; ".join(f'except {x["journal"]} ({x["why"]})' for x in FIX["not_written"])
    held = len(PENDING)
    with open(f"{ROOT}/lists/codebook.md", "w") as f:
        f.write(CODEBOOK.format(not_written=f" ({left})" if left else "", reply_by=reply_by_text(),
                                held_note=(f" {held} paper{'s are' if held > 1 else ' is'} held out of all-papers.csv until "
                                           f"{'they are' if held > 1 else 'it is'} named; {'their' if held > 1 else 'its'} corrections still count in the "
                                           f"journal tables.") if held else ""))


CODE = {"substantive": 0, "perfunctory": 1, "aware": 2, "unclear": 3}


def on_lists_json():
    """lists/on-lists.json, read by the census search (assets/data.js): for each listed paper, its place and list counts
    beside the census counts, and every citation whose label or standing the corrections changed, so a reader who
    follows "every citation" sees why the list's count differs from the census panel's labels."""
    kept = {r["pair_id"]: r["label"] for r in in_scope(corrected_rows())}
    why = {p: x["reason"] for x in FIX["exclude_citing"] for p in x["pairs"]}
    out = {}
    for p in listed:
        k, changed = p["pmid"], {}
        for r in ROWS:
            if r["retracted_pmid"] != k or r["retraction_reason"] == ADMIN:
                continue
            new = kept.get(r["pair_id"])
            if new is None and r["pair_id"] in RELABEL:
                new = RELABEL[r["pair_id"]]["new"]  # relabelled "unclear": out of the lists' scope, shown with its label
            if new is not None and new != r["label"]:
                changed[r["citing_pmcid"]] = {"label": CODE[new], "why": "full read " + day(RELABEL[r["pair_id"]]["date"])}
            elif new is None and r["label"] != "unclear":
                changed[r["citing_pmcid"]] = {"label": None, "why": why.get(r["pair_id"], "made before the retraction")}
        out[k] = {"rank": p["rank"], "support": p["support"], "judged": p["judged"], "census_support": by_census[k]["substantive"],
                  "census_judged": sum(by_census[k].values()), "full_read": day(FULL_READ["date"]) if k in FULL_READ["papers"] else "",
                  "changed": changed}
    json.dump({"about": "Written by tools/lists.py: the listed papers, their list counts beside the census counts, and every "
                        "citation whose label or standing the list's corrections changed (label: 0 cited as support, 1 mentioned "
                        "in passing, 2 flagged, 3 unclear, null left out).", "papers": out},
              open(f"{ROOT}/lists/on-lists.json", "w"), indent=0, sort_keys=True)


# Census-wide files: one row per retracted paper or citation in the census, unranked, public since the census release.
# They hold every paper, held ones included, and say nothing about the lists; every other served file must not
# name a held entry until it is named on the page (SOP H2).
CENSUS_WIDE = ("data/phase2/c/", "data/phase2/citations.csv", "data/phase2/contexts-", "data/phase2/paper_subjects.csv",
               "data/phase2/papers.json", "data/phase2/retraction_status.csv", "data/phase2/first_authors.json")
NOT_SERVED = ("tools/", ".git/", ".git", ".gitignore", ".assetsignore", "AGENTS.md", "README.md", "VISION.md", "FUNDING.md",
              "wrangler.toml", ".DS_Store")


def check_published():
    """Run by build.py after every file is written: no held entry may appear in any served file but the census-wide
    ones (23 Oct audit: the held place-8 paper was named in lists/all-papers.csv and list_corrections.json)."""
    ignored = [l.strip().rstrip("/") for l in open(f"{ROOT}/.assetsignore") if l.strip() and not l.startswith("#")]
    hits, claims = [], []
    for d, dirs, files in os.walk(ROOT):
        rel_d = os.path.relpath(d, ROOT)
        dirs[:] = [x for x in dirs if not (x.startswith(".") or (rel_d == "." and x in ignored) or x == "__pycache__")]
        for f in files:
            rel = os.path.normpath(os.path.join(rel_d, f))
            if rel.startswith(NOT_SERVED) or rel in ignored or rel.startswith(CENSUS_WIDE) or f.startswith("."):
                continue
            if rel.endswith((".png", ".jpg", ".woff2", ".ico")):
                continue
            data = open(os.path.join(d, f), "rb").read()
            hits += [f"{rel}: {e}" for e in PENDING if e.encode() in data]
            if FIX["not_written"] and rel.endswith((".html", ".csv", ".json", ".md", ".txt")):
                text = data.decode("utf-8", "replace")
                claims += [f"{rel}: {m.group(0)[:90]!r}" for m in SENT_CLAIM.finditer(text) if "except" not in m.group(0).lower()]
    if hits:
        stop("a held entry appears in a published file (keep it in tools/held.json until it is named):\n  " + "\n  ".join(hits))
    if claims:
        stop("a published file says everyone named was written to, without the not_written exception:\n  " + "\n  ".join(claims))


def check_final():
    """Stops the build if a confirmation the page prints still rests on a second reading that the full read reversed
    (23 Oct audit: Chen L, Oncogene 2017 printed 13 of 13 when the final verdict was lower). Recounts every entry's
    confirmations from the written second-reading.csv and compares them with the numbers on the page."""
    rows = list(csv.DictReader(open(f"{ROOT}/lists/second-reading.csv", newline="")))
    got = Counter((r["list"], r["entry"]) for r in rows if r["final_verdict"] == SUPPORT)
    want = {("paper", p["pmid"]): p["confirmed"] for p in L["papers"]}
    want.update({("journal", x["journal"]): x["confirmed"] for k in L["journals"] for x in L["journals"][k]})
    want.update({("author", f"{a['orcid']} {a['short']}"): a["citations_confirmed"] for a in A})
    bad = [f"{k}: page {v}, final verdicts {got[k]}" for k, v in want.items() if got[k] != v]
    stale = [c["pair_id"] for c in STALE_SUPPORT if any(r["pair_id"] == c["pair_id"] and r["final_verdict"] == SUPPORT for r in rows)]
    if bad or stale:
        stop("a confirmation counts a second reading the full read reversed:\n  " + "\n  ".join(bad + stale))


CODEBOOK = """# Lists downloads: what the columns mean

Written by tools/lists.py. Corrections applied on top of the generated data are in
/data/phase2/list_corrections.json, each with its source.

## Where dates and reasons come from

- `retraction_year_notice`, `reason_notice` (papers.csv, all-papers.csv): from the journal's retraction notice.
  `reason_source` names the notice. "not yet read" means we have not read that notice first-hand.
- `retraction_year_retraction_watch` (papers.csv, all-papers.csv): the year in the Retraction Watch database.
  It can differ from the notice; the census uses it except where list_corrections.json gives the notice date.
- `reason_group_retraction_watch` (papers.csv, all-papers.csv): grouped from Retraction Watch codes, not the notice's wording.
  A group such as "misconduct, fabrication or duplication" bundles reasons a given notice may never state.
- `retraction_reason` in /data/phase2/citations.csv: the same grouping, from Retraction Watch codes, not the notice's wording.
- `retraction_year` in /data/phase2/citations.csv: the Retraction Watch year.

## author-items.csv

One row per citation on the author list.
- `notice_reason_class`: results (the notice names a problem with the data, images or results, or says they cannot be
  relied on) or unclear (no reason, a vague one, or not yet read; still counted). Citations of work retracted only for
  reasons that do not touch the results (reused text, a duplicate of a result that stays published, authorship, ethics
  paperwork, copyright or a software licence, a wrong journal) are left out of every list and count here; they are
  published in excluded-works.csv and excluded-citations.csv.
- `reference_list_shows_retraction`: 1 if the citing paper's published reference list links the retraction notice or
  labels the work retracted. Such links are often added automatically during publication, from the cited record, so
  they do not show the authors knew.
- `timeline`: printed where the citing paper was submitted or accepted before the retraction.
- `citing_paper_retracted`: the citing paper has itself been retracted since.
- `retraction_year`: as printed in our letters, with later corrections.

## replies.csv

Everyone named was written to before publication{not_written}, and told that replies received by {reply_by} would be
summarised fairly on the page. Every reply gets the same treatment (one rule for everyone): a summary in our words, one short
verbatim quote, and any statement the writer supplied for publication, printed as written. One row per reply. The same fields are in /data/phase2/list_corrections.json under `replies`.
- `list`, `entry_id`: the entry the reply belongs to: an author's ORCID iD, a retracted paper's PMID or a citing
  journal's name. The build stops if the entry does not exist.
- `shown`: "on the page", printed under the entry; or "downloadable data only" for a paper retracted for reasons that do
  not touch its results, which is not named on the page.
- `received`: the date the reply reached us. `from_role`: who wrote, by role (the author, the editor).
- `reply_by`: the reply date stated in our letter to that entry. `late`: "received after the reply date" when the
  reply came later; a late reply is still printed, with its date.
- `summary`: two to four sentences in our words, giving the writer's main points, including those against us.
- `quote`: one short passage in the writer's own words (under 40 words), chosen by a fixed rule: the sentence that states
  their main point. Spelling and grammar are left as written.
- `statement`: a statement the writer supplied for publication (for example a note for later authors), printed as
  written, paragraphs separated by a blank line; empty if none was supplied. Greetings, sign-offs and contact details are
  left off.
- `our_response`: what changed because of the reply, or why the entry stands, with the facts.
- `changes_since_letter`: every change to the entry since our letter, separated by " | ", whether the reply prompted it
  or a rule applied to every entry did.
- Not published: where each reply came from (kept privately, so the build can check every reply has a source).
  No reply is left out, and no one is asked for permission to be quoted; replies are never trimmed to win a point.
  Contact details and third-party personal data are removed from everything printed. An automatic reply or a bare
  acknowledgement is not a reply and is not summarised.

## second-reading.csv

Every citation read a second time, limited to citations still in scope after the corrections. Readings of citations to
work retracted for reasons that do not touch the results are not included.
- `second_reading`: the verdict of the second reading. `note`: the reader's one-line reason.
- `final_verdict`: the verdict the lists count. It is the second reading, unless a later full-text check of the same
  citation (list_corrections.json `relabel`) gave another label; then it is that label.
- `reading_round`: which reading gave the final verdict: "second reading", or "full read" with its date (for a few
  papers near the last place, "full read, two blind readings and a third reader").
- All of these are AI readings. Everyone named was sent the evidence{not_written} and asked to tell us if a reading is
  wrong.

## all-papers.csv and all-journals.csv

Every retracted paper and citing journal in the lists' scope, ranked by the count of citations cited as support. The
counts carry the corrections in list_corrections.json (label corrections from the full-text checks, dates from the
notices, citations made before a retraction left out); only the listed entries and the papers near the last place were
read again. `census_cited_as_support` and `census_judged` (all-papers.csv) give the census labels alone, so every
difference can be traced.{held_note}

## excluded-works.csv and excluded-citations.csv

The papers retracted only for reasons that do not touch the results, and every judged citation of them made after the
retraction, with the census label. They are left out of every count and list, not hidden.
- `notice_says` (excluded-works.csv): the notice's reason, in its own words where quoted.
- `census_label`: substantive (cited as support), perfunctory (mentioned in passing) or aware (flagged as retracted
  or unreliable). Not read a second time.
"""


def latest_correction():
    """The newest dated correction applied to the lists (list_corrections.json and the held entries' corrections)."""
    dates = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "date" and isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                    dates.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(FIX)
    return max(dates)


def sent_line():
    """Who was sent the evidence, with the page's stated exceptions (review of 23 Oct fixes: the meta description and
    the checked box said everyone named was written to, but Heliyon is named and was not)."""
    left = "; ".join(f'{esc(x["journal"])} ({esc(x["why"])})' for x in FIX["not_written"])
    return (f'Everyone named was sent the evidence{", except " + left + "," if left else ""} and asked to tell us if a '
            f'reading is wrong')


# a sentence saying everyone named was written to or sent the evidence must state the exception (check_published)
SENT_CLAIM = re.compile(r"(?:everyone|everybody|the people|all those) named (?:was|were) (?:written to|sent)[^.]*", re.I)


def checked_box():
    """One account of how each list was checked, from the data (23 Oct audit: the page described it four ways, and the
    lede said every entry's citations were read a second time, which is not true of the journals)."""
    jr = [x["read"] for k in L["journals"] for x in L["journals"][k]]
    nfull, ntwice = len(FULL_READ["papers"]), len(FULL_READ.get("second_read", []))
    return (f'<div class="lbox" id="checked"><h2>How these lists were checked</h2><dl>'
            f'<dt>Papers</dt><dd>Every citation counted as support was read again in full ({day(FULL_READ["date"])}) for each listed paper '
            f'and each paper near the last place, {nfull} papers in all. For the {ntwice} nearest the last place, each '
            f'citation was read twice, independently, and a third reading settled any disagreement. The {n(len(left))} papers left off '
            f'after reading were judged on their second reading, not read in full.</dd>'
            f'<dt>Journals</dt><dd>A random sample of {min(jr)} to {max(jr)} support citations per journal was read again, not every citation.</dd>'
            f'<dt>Authors</dt><dd>Every support citation in every listed author\'s papers was read again ({n(sum(a["citations_read"] for a in A))} in all).</dd>'
            f'</dl><p>All of these are AI readings. {sent_line()}; replies are printed beside their entries.</p></div>')


def full_tables_block():
    """A plain pointer near the top of the page to the two full ranked tables (owner, 23 Oct 2026, "Lists in waves").
    Its counts are the rows just written to the CSV files, and must equal the counts the "How we checked" item gives."""
    if FULL_ROWS["papers"] != PAPER_SCOPE - len(PENDING & set(by_p)) or FULL_ROWS["journals"] != len(by_j):
        stop(f"full tables: the CSV rows {FULL_ROWS} differ from the page's counts")
    held = (" One held paper is left out until it is named." if len(PENDING) == 1 else
            f" {len(PENDING)} held papers are left out until they are named.") if PENDING else ""
    return (f'<div class="lbox" id="full"><h2>The full ranked tables</h2>'
            f'<p>Every retracted paper ({n(FULL_ROWS["papers"])}) and every citing journal ({n(FULL_ROWS["journals"])}) in the '
            f'lists\' scope, ranked by the citations the census AI models labelled as support, with this page\'s corrections '
            f'applied. Only the listed entries and the papers near the last place were read again.{held}</p>'
            f'<p><a href="/lists/all-papers.csv" download>All {n(FULL_ROWS["papers"])} papers (CSV)</a> · '
            f'<a href="/lists/all-journals.csv" download>All {n(FULL_ROWS["journals"])} journals (CSV)</a> · '
            f'<a href="#full-tables">What the tables hold</a></p></div>')


def fill(body):
    if "<!--lists:" not in body:
        return body
    full_tables()
    seen = {}
    for c in CHECKS: seen[c["pair_id"]] = c["final_verdict"]  # a citation read for two lists counts once
    v = Counter(seen.values())
    other = v["other: wrong reference, or not about the paper"]
    reading_line = (f"Of {n(len(seen))} different citations the census called support and we read again, {n(v[SUPPORT])} "
                    f"({pct(v[SUPPORT] / len(seen))}) held up after every reading. {n(v['mentioned it in passing'])} only mentioned the paper in passing, "
                    f"{n(v['flagged it as retracted or unreliable'])} flagged it as retracted or unreliable, and {n(other)} were "
                    f"about something else, most often because the reference pointed at the wrong paper. These citations come from the top "
                    f"of each list, so they are not a rate for the whole census.")
    parts = {"reading": reading_line, "papers": papers_table(), "journals": journals_block(), "authors": authors_table(),
             "scope": f"{n(len(J))} judged citations to {n(PAPER_SCOPE)} retracted papers",
             "excluded": (f"They are not hidden: {n(sum(r['label'] == 'substantive' for r in X))} later citations use "
                          f"{n(len({r['retracted_pmid'] for r in X if r['label'] == 'substantive'}))} such papers as support, from "
                          f"{n(len({r['citing_pmcid'] for r in X if r['label'] == 'substantive'}))} citing papers. "
                          f'<a href="/lists/excluded-works.csv" download>The papers</a> · '
                          f'<a href="/lists/excluded-citations.csv" download>every citation</a>, labelled with the reason.'),
             "replies-intro": replies_intro(), "papers-all": n(PAPER_SCOPE - len(PENDING & set(by_p))), "journals-all": n(len(by_j)),
             "as-of": f"Census data as of {AS_OF}; corrections through {day(latest_correction())}", "provisional": PROVISIONAL,
             "checked": checked_box(), "sent": sent_line(), "full": full_tables_block(),
             "full-tables": (f"They are ranked by count with the corrections in list_corrections.json applied: {n(CHANGED_PAPERS)} papers' counts "
                             f"differ from the census labels alone, and the file gives both. Only the listed entries and the papers near "
                             f"the last place were read again." + ((" One held paper is left out until it is named." if len(PENDING) == 1 else
                                                                   f" {len(PENDING)} held papers are left out until they are named.") if PENDING else ""))}
    for k, v in parts.items():
        body = body.replace(f"<!--lists:{k}-->", v)
    return body
