"""Phase 2 census charts for build.py: plain HTML and CSS (crisp text at any width, readable
without JavaScript), drawn from the published data files so a chart can never disagree with
census.json. Every number is recomputed from citations.csv and checked against census.json;
any mismatch stops the build. Also writes one CSV per chart for download, and the key facts
for the press page. Rates always come from k/n and are rounded once."""
import csv, datetime, hashlib, html, json, os, re, urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://sanecite.com"
ADMIN = "administrative (no fault found in the science)"
P2 = f"{ROOT}/data/phase2"
CENSUS = json.load(open(f"{P2}/census.json"))
ROWS = list(csv.DictReader(open(f"{P2}/citations.csv", newline="")))
if not CENSUS.get("data_as_of"):
    raise SystemExit("charts: census.json has no data_as_of date; every chart prints it")
_d = datetime.date.fromisoformat(CENSUS["data_as_of"])
AS_OF = f"{_d.day} {_d:%b %Y}"  # e.g. 14 Oct 2026
# Fingerprint of everything the share images show. Image links carry it (?v=), so a browser fetches new
# images at once, and build.py draws the images again whenever it changes.
IMG_KEY = hashlib.sha256(b"".join(open(f"{ROOT}/{f}", "rb").read() for f in (
    "data/phase2/census.json", "data/phase2/citations.csv", "data/phase2/by_subject.json", "data/phase2/paper_subjects.csv",
    "data/stage3/batch6-result.json",
    "assets/site.css", "tools/charts.py",
    "tools/render_charts.mjs"))).hexdigest()[:10]
LAB = {"substantive": "s", "perfunctory": "p", "aware": "a"}
YEARS_DRAWN = 20  # years after retraction drawn one by one; later ones are in the table and CSV
SRC = "SaneCite Phase 2 census"
POP = "open-access papers citing retracted biomedical papers (PubMed-indexed, retracted 1990–2023)"
PROVISIONAL = "Read by three AI models; pending human review."
PILL = "Pending human review"
CI_NOTE = ("95% confidence intervals (the likely range) come from re-running the numbers 400 times, "
           "drawing whole retracted papers at random (a cluster bootstrap).")
# The one wording used everywhere for the three labels.
WORDS = {"substantive": "treated it as support", "perfunctory": "mentioned it in passing",
         "aware": "flagged it as retracted or unreliable"}
FIELD_NAMES = {"basic life sciences only": "Basic life sciences only", "health sciences only": "Health sciences only",
               "basic life and health sciences": "Both basic life and health sciences", "other fields": "Includes another subject",
               "?": "Business and technology only (not grouped)"}


def judged(row):
    """The headline scope: paperwork (administrative) retractions and unclear labels left out."""
    return row["retraction_reason"] != ADMIN and row["label"] != "unclear"


def check(name, got, want):
    if got != want:
        raise SystemExit(f"charts: {name} does not match census.json: {got} != {want}")


def n(x):
    return f"{x:,}"


def pct(rate, dp=1):
    return f"{100 * rate:.{dp}f}%"


def rt(stat):
    """Rate from its counts. census.json rates are already rounded to 4 places; rounding those
    again gives 40.8% for 21,037/51,626 = 40.749%, the double-rounding error in the SOP."""
    return stat["k"] / stat["n"] if stat["n"] else 0.0


def ci(stat, unit="%"):
    lo, hi = stat["ci95"]
    return f"{100 * lo:.1f}–{100 * hi:.1f}{unit}"


def rc(stat):
    """Rate with its interval in one table cell; a zero count says so instead of a 0–0 interval."""
    if stat["k"] == 0:
        return f"0 of {n(stat['n'])}"
    return f"{pct(rt(stat))} <small>({ci(stat, '')})</small>"


def esc(s):
    return html.escape(str(s), quote=True)


def cap(s):
    return s[:1].upper() + s[1:]


def write_csv(name, header, rows):
    os.makedirs(f"{ROOT}/charts", exist_ok=True)
    with open(f"{ROOT}/charts/{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def share(cid, caption):
    """Download, copy and share row. Plain links: no third-party scripts."""
    page = f"{SITE}/charts/{cid}.html"
    q = urllib.parse.quote
    return f"""<div class="vz-share" role="group" aria-label="Share this chart">
  <a class="vz-btn solid" href="/charts/{cid}.png?v={IMG_KEY}" download="sanecite-{cid}.png">Download image</a>
  <a class="vz-btn" href="/charts/{cid}-square.png?v={IMG_KEY}" download="sanecite-{cid}-square.png">Square image</a>
  <button type="button" class="vz-btn" data-copy="{esc(caption + ' ' + page)}">Copy caption</button>
  <button type="button" class="vz-btn" data-copy="{esc(page)}">Copy link</button>
  <a class="vz-btn" href="https://x.com/intent/post?text={q(caption)}&amp;url={q(page)}" target="_blank" rel="noopener">Post on X</a>
  <a class="vz-btn" href="https://bsky.app/intent/compose?text={q(caption + ' ' + page)}" target="_blank" rel="noopener">Bluesky</a>
  <a class="vz-btn" href="https://www.linkedin.com/sharing/share-offsite/?url={q(page)}" target="_blank" rel="noopener">LinkedIn</a>
  <a class="vz-btn" href="/charts/{cid}.csv" download>Data (CSV)</a>
</div>"""


META = {}  # chart id -> dict(title, sub, caption, alt); chart pages use it for <title>, description, share text


def data_table(table, title):
    """Every data table gets a caption and column headers with scope="col", for screen readers (audit 23 Oct).
    The caption is visually hidden: the chart title above already says what the table holds."""
    name = esc(re.sub(r"<[^>]+>", "", title)).rstrip(".")
    parts = table.split("<table>")
    out = parts[0]
    for i, rest in enumerate(parts[1:], 1):
        lead = re.search(r"<p><b>([^<]+)</b>[^<]*</p>$", out)  # a bold lead-in just before a table names it
        part = lead.group(1).lower() if lead else ("the numbers" if i == 1 else f"table {i}")
        out += f'<table><caption class="vh">{name}: {part}</caption>' + rest
    return out.replace("<th>", '<th scope="col">')


def figure(cid, kicker, title, sub, body, note, source, table, caption, hook, focus="", card_note="", drawn=None, simple="",
           card_src="", as_of="", pill=""):
    """hook = (big number, short line, colour class): the share image leads with it.
    simple = the plain bar view from simple_bars(); when given it is the default view and the share image,
    and body (the detailed chart, with likely ranges) sits behind a Simple / Detailed switch.
    note = one plain caveat line shown under the chart, on the page and on the image.
    focus = 's' or 'a': the share image keeps only that column of a forest plot."""
    big, line, tone = hook
    stage, _, question = kicker.partition(" · ")
    count = f"{n(JUDGED)} citations" + (f" ({n(drawn)} drawn)" if drawn else "")
    META[cid] = {"title": title, "sub": sub, "caption": caption, "alt": f"Chart: {big} {line} Source: SaneCite."}
    if simple:
        body = ('<div class="vz-toggle vz-view" role="group" aria-label="View"><button type="button" aria-pressed="true" '
                'data-view="simple">Simple</button><button type="button" aria-pressed="false" data-view="detail">Detailed</button></div>'
                + simple + body.replace('<div class="vz-body', '<div class="vz-detail vz-body', 1))
    return f"""<figure class="vz{' focus-' + focus if focus else ''}" id="vz-{cid}" data-chart="{cid}"{' data-view="simple"' if simple else ''}>
<figcaption class="vz-head"><span class="eyebrow"><span class="vz-stage">{stage} · </span>{question}</span><span class="vz-pill" aria-hidden="true">{pill or PILL}</span>
<h3 class="vz-title">{title}</h3><p class="vz-sub">{sub}</p>
<div class="vz-hook {tone}" aria-hidden="true"><b>{big}</b><span>{line}</span></div></figcaption>
{body}
{f'<p class="vz-note">{note}</p>' if note else ''}
{f'<p class="vz-note-card">{card_note}</p>' if card_note else ''}
<p class="vz-src">{source} Data as of {as_of or AS_OF}.</p>
<p class="vz-src-card">{card_src or f"Source: SaneCite Phase 2 census, {count}, data as of {AS_OF}"} · sanecite.com/charts</p>
<span class="vz-brand" aria-hidden="true">sanecite.com</span>
<details class="vz-data"><summary>Show the numbers</summary>{data_table(table, title)}</details>
{share(cid, caption)}
</figure>"""


# ---------------------------------------------------------------- the three labels, overall
J = [r for r in ROWS if judged(r)]
overall = Counter(r["label"] for r in J)
check("judged citations", len(J), CENSUS["judged"])
for lab in LAB:
    check(f"{lab} count", overall[lab], CENSUS[lab]["k"])
S, P, A = (CENSUS[k] for k in ("substantive", "perfunctory", "aware"))
JUDGED = CENSUS["judged"]
PAPERS = S["papers"]
CORR = CENSUS["substantive_corrected"]
CORR_NOTE = (f"Not corrected for reader error. Corrected using one AI reader's checks of 150 citations, the estimate is "
             f"{pct(CORR['rate'])} (95% CI {ci(CORR)}).")


def out_of_100():
    """Largest-remainder rounding, so the three groups make exactly 100 dots."""
    exact = {k: 100 * CENSUS[k]["k"] / JUDGED for k in LAB}
    dots = {k: int(v) for k, v in exact.items()}
    for k in sorted(exact, key=lambda k: exact[k] - dots[k], reverse=True)[: 100 - sum(dots.values())]:
        dots[k] += 1
    check("dots", sum(dots.values()), 100)
    order = ("substantive", "perfunctory", "aware")
    grid = "".join(f'<i class="d {LAB[k]}"></i>' * dots[k] for k in order)
    key = "".join(
        f'<li class="{LAB[k]}" data-k="{LAB[k]}"><i class="d {LAB[k]}"></i><b>{dots[k]}</b><span>{WORDS[k]}'
        f'<small>{pct(rt(CENSUS[k]))} · {n(CENSUS[k]["k"])} of {n(JUDGED)}</small></span></li>' for k in order)
    body = (f'<div class="vz-body dots-wrap"><div class="dots" role="img" aria-label="100 dots: {dots["substantive"]} '
            f'for treated it as support, {dots["perfunctory"]} for mentioned it in passing, {dots["aware"]} for flagged it as retracted or unreliable.">{grid}</div>'
            f'<div><p class="vz-lead">Out of every 100 citations:</p><ul class="vz-key">{key}</ul></div></div>')
    table = ("<table><tr><th>Label</th><th>Citations</th><th>Share (95% CI, %)</th></tr>"
             + "".join(f"<tr><td>{cap(WORDS[k])}</td><td>{n(CENSUS[k]['k'])}</td><td>{rc(CENSUS[k])}</td></tr>" for k in order)
             + f"<tr><td>All judged</td><td>{n(JUDGED)}</td><td>100%</td></tr></table>"
             f"<p>{n(JUDGED)} citations to {n(PAPERS)} retracted papers, each made in a year after the retraction. "
             f"Left out: {n(CENSUS['administrative_pairs'])} citations to paperwork retractions (no fault found in the science) "
             f"and {n(CENSUS['unclear_labels'])} the three readers could not decide. {CORR_NOTE} {CI_NOTE}</p>")
    write_csv("out-of-100", ["label", "citations", "judged_citations", "share", "ci95_low", "ci95_high", "dots_of_100"],
              [[WORDS[k], CENSUS[k]["k"], JUDGED, rt(CENSUS[k]), *CENSUS[k]["ci95"], dots[k]] for k in order])
    caption = (f"Of every 100 citations to a retracted paper, {dots['substantive']} still treat it as support and only "
               f"{dots['aware']} flag it as retracted or unreliable ({pct(rt(S))} and {pct(rt(A))} of {n(JUDGED)} citations). "
               f"Source: {SRC}, provisional.")
    return figure(
        "out-of-100", "Phase 2 census · what later papers do with a retracted study",
        f"{pct(rt(S))} of citations to retracted papers still treat them as support.",
        f"Out of every 100 citations made after a paper was retracted, {dots['substantive']} treat it as support, "
        f"{dots['perfunctory']} mention it in passing, and just {dots['aware']} flag it as retracted or unreliable.",
        body, "",
        f"Source: {SRC}: {n(JUDGED)} citations to {n(PAPERS)} retracted papers, from {POP}. {PROVISIONAL}", table, caption,
        (pct(rt(S)), "of citations to retracted papers still treat them as support.", "s"))


def years_after():
    by = defaultdict(Counter)
    for r in J:
        by[int(r["citing_year"]) - int(r["retraction_year"])][r["label"]] += 1
    years = sorted(by)  # taken before the bucket sums below, which would add empty years to the defaultdict
    buckets = {"1-2": (1, 2), "3-5": (3, 5), "6-10": (6, 10), "11+": (11, 99)}
    for b, (lo, hi) in buckets.items():
        c = sum((by.get(y, Counter()) for y in range(lo, hi + 1)), Counter())
        check(f"years {b} n", sum(c.values()), CENSUS["by_years_after"][b]["substantive"]["n"])
        check(f"years {b} support", c["substantive"], CENSUS["by_years_after"][b]["substantive"]["k"])
        check(f"years {b} flagged", c["aware"], CENSUS["by_years_after"][b]["aware"]["k"])
    check("no citation in the retraction year or before", years[0], 1)
    drawn = sum(sum(by[y].values()) for y in by if y <= YEARS_DRAWN)
    later = JUDGED - drawn
    top_y = max(range(1, YEARS_DRAWN + 1), key=lambda y: sum(by[y].values()))
    top = sum(by[top_y].values())
    cols, rows = [], []
    for y in range(1, years[-1] + 1):
        c = by.get(y, Counter()); t = sum(c.values()); s, p, a = (c[k] for k in LAB)
        rows.append([y, t, s, p, a, s / t if t else "", a / t if t else ""])
        if y > YEARS_DRAWN:
            continue
        lab = f'<span class="yl">{y}</span>' if y in (1, 5, 10, 15, 20) else ""
        cnt = f'<span class="yc">{t / 1000:.1f}k</span>' if t >= 1000 else f'<span class="yc">{t}</span>'
        cols.append(
            f'<div class="yr" role="img" tabindex="0" data-y="{y}" data-t="{t}" data-s="{s}" data-p="{p}" data-a="{a}" '
            f'aria-label="{y} year{"" if y == 1 else "s"} after retraction: {n(t)} citations, {pct(s / t)} treated it as support, '
            f'{pct(a / t)} flagged it as retracted or unreliable">'
            f'<div class="ystack" style="--t:{t / top:.4f}"><i class="st s" style="--v:{s / t:.4f}"></i>'
            f'<i class="st p" style="--v:{p / t:.4f}"></i><i class="st a" style="--v:{a / t:.4f}"></i></div>'
            f'{cnt}{lab}</div>')
    early, late = CENSUS["by_years_after"]["1-2"]["substantive"], CENSUS["by_years_after"]["11+"]["substantive"]
    f_s, t_s = rt(early), rt(late)
    yaxis = "".join(f'<span style="--y:{v}">{v}%</span>' for v in (100, 50, 0))
    body = (f'<div class="vz-body"><div class="vz-toggle" role="group" aria-label="Show as">'
            f'<button type="button" aria-pressed="true" data-mode="share">Percent</button>'
            f'<button type="button" aria-pressed="false" data-mode="count">Count</button></div>'
            f'<div class="years" data-mode="share" style="--avg:{rt(S):.4f}">'
            f'<div class="yaxis" aria-hidden="true">{yaxis}</div>'
            f'<div class="ycols">{"".join(cols)}<div class="yavg" aria-hidden="true"><span>All years: {pct(rt(S))}</span></div></div></div>'
            f'<p class="yx">Years after retraction <span class="yx-n">· small numbers = citations that year · tallest: '
            f'{n(top)} in year {top_y}</span></p>'
            f'<ul class="vz-key inline"><li class="s"><i class="d s"></i>Treated it as support</li><li class="p"><i class="d pf"></i>Mentioned it in passing</li>'
            f'<li class="a"><i class="d a"></i>Flagged it as retracted or unreliable</li></ul><p class="vz-tip" aria-live="polite"></p></div>')
    bt = CENSUS["by_years_after"]
    table = ("<table><tr><th>Years after</th><th>Citations</th><th>Treated it as support (95% CI, %)</th><th>Flagged it (95% CI, %)</th></tr>"
             + "".join(f"<tr><td>{b.replace('-', '–')}</td><td>{n(bt[b]['substantive']['n'])}</td><td>{rc(bt[b]['substantive'])}</td>"
                       f"<td>{rc(bt[b]['aware'])}</td></tr>" for b in buckets) + "</table>"
             f"<p>Bars count citations made that many calendar years after the retraction year (citations in the retraction year "
             f"itself are not counted). The {n(later)} citations made {YEARS_DRAWN + 1} to {years[-1]} years after are in the table "
             f"and the CSV, not drawn. {CI_NOTE}</p>")
    write_csv("years-after", ["years_after", "citations", "cited_as_support", "passing", "flagged", "share_support", "share_flagged"], rows)
    caption = (f"More than ten years after a retraction, {pct(t_s)} of citations still treat the paper as support "
               f"({pct(f_s)} in the first two years). Source: {SRC}, provisional.")
    return figure(
        "years-after", "Phase 2 census · does time fix it?",
        f"{pct(t_s)} of citations still treat a retracted paper as support more than ten years later.",
        f"In the first two years after a retraction it is {pct(f_s)}. Only a few in a hundred ever flag the paper as "
        f"retracted or unreliable.",
        body,
        "Each bar mixes papers retracted in different years. Recent retractions can only appear in the early bars, "
        "so part of the drop comes from which papers are old enough to count.",
        f"Source: {SRC}: {n(JUDGED)} citations from {POP}<span class=\"only-detail\">; the year bars show the {n(drawn)} made within "
        f"{YEARS_DRAWN} years</span>. {PROVISIONAL}",
        table, caption,
        (pct(t_s), "of citations still treat a retracted paper as support more than ten years after the retraction.", "s"),
        card_note="Bars mix papers retracted in different years: part of the drop is which papers are old enough to count.",
        simple=simple_bars("Treated it as support, by years since the retraction",
                           [(lab, rt(bt[b]["substantive"]), "s", True) for b, lab in
                            (("1-2", "1–2 years after"), ("3-5", "3–5 years"), ("6-10", "6–10 years"), ("11+", "More than 10 years"))]))


SCALE = {"substantive": 0.6, "aware": 0.1}  # default axis maximum per metric; a chart may widen one
HEAD = {"substantive": "Treated it as support", "aware": "Flagged it as retracted or unreliable"}


def track(name, st, metric, avg, scale):
    """One rate with its 95% interval. The value label goes right of the interval unless that
    would sit on the dashed 'all' line or run off the axis; then it goes left."""
    sc = scale[metric]; s = st[metric]; lo, hi = s["ci95"]; r = rt(s)
    x_lo, x_hi, x_avg, w = lo / sc * 100, hi / sc * 100, avg / sc * 100, 17
    x_r = r / sc * 100
    right_ok = x_hi + w <= 100 and not (x_hi - 1 < x_avg < x_hi + w)
    left_ok = x_lo - w >= 0 and not (x_lo - w < x_avg < x_lo + 1)
    if right_ok:
        label = f'style="--x:{x_hi:.4f}"'
    elif left_ok:
        label = f'class="l" style="--x:{x_lo:.4f}"'
    else:  # no room either side: sit above the dot
        label = f'class="t" style="--x:{x_r:.4f}"'
    
    words = f"{name}: {HEAD[metric].lower()} {pct(r)}, likely range {100 * lo:.1f} to {100 * hi:.1f}%" if s["k"] else f"{name}: {HEAD[metric].lower()} 0 of {n(s['n'])}"
    return (f'<span class="ci-track {LAB[metric]}" role="img" aria-label="{esc(words)}" style="--avg:{x_avg:.4f};--d:{x_r:.4f}">'
            f'<i class="ci-bar" style="--lo:{x_lo:.4f};--hi:{x_hi:.4f}"></i>'
            f'<b class="ci-dot" style="--x:{x_r:.4f}"></b><em {label}>{pct(r)}</em></span>')


def forest(groups, scale=SCALE):
    """Rows of groups; two columns: treated it as support, flagged it. groups: [(name, note, stat|None)]."""
    def axis(metric):
        sc = scale[metric]
        return "".join(f'<span style="--x:{q:.2f}">{sc * 100 * q:g}%</span>' for q in (0, .25, .5, .75, 1))
    head = (f'<div class="fo-head" aria-hidden="true"><span></span>'
            f'<span class="s">{HEAD["substantive"]}<small><i></i>dashed line = all citations, {pct(rt(S))}</small></span>'
            f'<span class="a">{HEAD["aware"]}<small><i></i>dashed line = all citations, {pct(rt(A))}</small></span></div>'
            f'<div class="fo-axis" aria-hidden="true"><span></span><span class="ci-axis s">{axis("substantive")}</span>'
            f'<span class="ci-axis a">{axis("aware")}</span></div>')
    rows = []
    for name, note, st in groups:
        extra = " fo-extra" if name.startswith("Paperwork") else ""
        if st is None:
            rows.append(f'<div class="ci-sep fo-extra">{esc(name)}</div>'); continue
        rows.append(f'<div class="fo-row{extra}"><span class="ci-lab">{esc(name)}<small>{note}</small></span>'
                    f'{track(name, st, "substantive", rt(S), scale)}{track(name, st, "aware", rt(A), scale)}</div>')
    return f'<div class="vz-body forest">{head}{"".join(rows)}</div>'


def ci_table(groups):
    out = "<table><tr><th>Group</th><th>Citations</th><th>Treated it as support (95% CI, %)</th><th>Flagged it (95% CI, %)</th></tr>"
    for name, note, st in groups:
        if st is None: continue
        out += f"<tr><td>{esc(name)}</td><td>{n(st['substantive']['n'])}</td><td>{rc(st['substantive'])}</td><td>{rc(st['aware'])}</td></tr>"
    return out + "</table>"


def forest_csv(name, groups):
    write_csv(name, ["group", "citations", "cited_as_support", "share_support", "support_ci95_low", "support_ci95_high",
                     "flagged", "share_flagged", "flagged_ci95_low", "flagged_ci95_high"],
              [[g, st["substantive"]["n"], st["substantive"]["k"], rt(st["substantive"]), *st["substantive"]["ci95"],
                st["aware"]["k"], rt(st["aware"]), *st["aware"]["ci95"]] for g, _, st in groups if st])


def simple_bars(lead, rows, foot=""):
    """The default view: one measure, bars from zero, the value on the end of each bar.
    rows: [(label, rate, colour class, highlighted)]. The longest bar fills the track, so lengths
    stay in proportion to the rates. Highlighted bars take the colour; the rest are grey context."""
    top = max(r for _, r, _, _ in rows)
    bars = "".join(f'<span class="sb-lab">{esc(lab)}</span><span class="sb-bar {tone}{" hl" if hl else ""}" style="--v:{r / top:.4f}">'
                   f'<i></i><b>{pct(r)}</b></span>' for lab, r, tone, hl in rows)
    words = esc(f"{lead}: " + "; ".join(f"{lab} {pct(r)}" for lab, r, _, _ in rows))
    return (f'<div class="vz-body vz-simple"><p class="sb-lead">{lead}</p><div class="sb{" many" if len(rows) > 5 else ""}" role="img" aria-label="{words}">{bars}</div>'
            + (f'<p class="sb-foot">{foot}</p>' if foot else "") + "</div>")


def by_reason():
    br = CENSUS["by_reason_all"]
    g = defaultdict(Counter)
    for r in ROWS:
        if r["label"] != "unclear": g[r["retraction_reason"]][r["label"]] += 1
    for k, st in br.items():
        check(f"reason {k} n", sum(g[k].values()), st["substantive"]["n"])
        check(f"reason {k} support", g[k]["substantive"], st["substantive"]["k"])
        check(f"reason {k} flagged", g[k]["aware"], st["aware"]["k"])
    mk, ek, ok = "misconduct, fabrication or duplication", "error or unreliable results", "other or unstated"
    names = {mk: "Misconduct, fabrication or duplication", ek: "Error or unreliable results", ok: "Other or no reason given",
             ADMIN: "Paperwork retractions (no fault found in the science)"}
    groups = [(names[k], f"{n(br[k]['substantive']['n'])} citations", br[k]) for k in (mk, ek, ok)]
    groups += [("Not in the headline figure", "", None), (names[ADMIN], f"{n(br[ADMIN]['substantive']['n'])} citations", br[ADMIN])]
    mis, err = br[mk], br[ek]
    check("flagged intervals do not overlap", mis["aware"]["ci95"][1] < err["aware"]["ci95"][0], True)
    table = (ci_table(groups) + f"<p>Reason groups follow the Retraction Watch reason codes. Paperwork retractions (out of date, "
             f"replaced, moved journal, publisher duplicate) find no fault in the science and are reported apart. {CI_NOTE}</p>")
    forest_csv("by-reason", groups)
    caption = (f"Papers retracted for misconduct are cited as support as often as those retracted for error "
               f"({pct(rt(mis['substantive']))} vs {pct(rt(err['substantive']))}), but far fewer citations flag the problem "
               f"({pct(rt(mis['aware']))} vs {pct(rt(err['aware']))}). Source: {SRC}, provisional.")
    return figure(
        "by-reason", "Phase 2 census · does the reason matter?",
        f"Only {pct(rt(mis['aware']))} of citations to papers retracted for misconduct flag them as retracted or unreliable.",
        f"For papers retracted for error it is {pct(rt(err['aware']))}. Both are still cited as support about 4 times in 10 "
        f"({pct(rt(mis['substantive']))} and {pct(rt(err['substantive']))}).",
        forest(groups), "",
        f"Source: {SRC}: {n(JUDGED)} citations from {POP}; {n(CENSUS['administrative_pairs'])} more, to paperwork retractions, "
        f"are reported apart.<span class=\"only-detail\"> Dot = estimate; line = 95% CI.</span> {PROVISIONAL}",
        table, caption,
        (pct(rt(mis["aware"])), f"of citations to papers retracted for misconduct flag the problem, against "
                                f"{pct(rt(err['aware']))} for error.", "a"), focus="a",
        simple=simple_bars("Flagged it as retracted or unreliable, by reason for the retraction",
                           [(names[mk], rt(mis["aware"]), "a", True), (names[ek], rt(err["aware"]), "a", True),
                            (names[ok], rt(br[ok]["aware"]), "a", False)],
                           f"Misconduct and error are still cited as support about as often: {pct(rt(mis['substantive']))} and "
                           f"{pct(rt(err['substantive']))}."))


def by_field():
    """Simple view: every Retraction Watch subject (a later check, not in the registered plan; census repo
    scripts/subject_breakdown.py). Detailed view: the registered grouping by each paper's whole set of codes."""
    bf = CENSUS["by_field"]
    g = defaultdict(Counter)
    for r in J: g[r["field"]][r["label"]] += 1
    for k, st in bf.items():
        check(f"field {k} n", sum(g[k].values()), st["substantive"]["n"])
        check(f"field {k} support", g[k]["substantive"], st["substantive"]["k"])
        check(f"field {k} flagged", g[k]["aware"], st["aware"]["k"])
    sub = json.load(open(f"{P2}/by_subject.json"))
    codes = {r["retracted_pmid"]: r["subjects"].split(";") for r in csv.DictReader(open(f"{P2}/paper_subjects.csv", newline=""))}
    gs = defaultdict(Counter)
    for r in J:
        for c in codes[r["retracted_pmid"]]: gs[c][r["label"]] += 1
    check("subject breakdown base", sub["judged"], JUDGED)
    sb = sub["subjects"]
    for c, st in sb.items():
        check(f"subject {c} n", sum(gs[c].values()), st["substantive"]["n"])
        check(f"subject {c} support", gs[c]["substantive"], st["substantive"]["k"])
        check(f"subject {c} flagged", gs[c]["aware"], st["aware"]["k"])
    sorder = sorted(sb, key=lambda c: -rt(sb[c]["substantive"]))
    low, hi = (f(rt(sb[c]["substantive"]) for c in sorder) for f in (min, max))
    alo, ahi = (f(rt(sb[c]["aware"]) for c in sorder) for f in (min, max))
    small = min(sorder, key=lambda c: sb[c]["substantive"]["n"])
    span = f"{100 * low:.0f}% to {100 * hi:.0f}%"
    order = sorted((k for k in bf if k != "?"), key=lambda k: -rt(bf[k]["substantive"]))
    groups = [(FIELD_NAMES[k], f"{n(bf[k]['substantive']['n'])} citations", bf[k]) for k in order]
    nf = bf["?"]["substantive"]["n"]
    subj_groups = [(sb[c]["name"], f"{n(sb[c]['substantive']['n'])} citations", sb[c]) for c in sorder]
    table = ("<p><b>By subject</b> (a later check, not in the registered plan). A paper with several subjects counts "
             "under each, so the groups overlap.</p>" + ci_table(subj_groups) +
             "<p><b>The registered grouping</b> sorts each paper by its whole set of Retraction Watch subject codes: basic "
             "life sciences (BLS) only, health sciences (HSC) only, both, or a set that includes any other subject (such as "
             "chemistry or psychology, often alongside BLS or HSC).</p>" + ci_table(groups + [(FIELD_NAMES["?"], "", bf["?"])]) +
             f"<p>The registered rule's code pattern skipped the business and technology code (B/T), so {n(nf)} citations to "
             f"papers coded only B/T are left out of its groups; they are in the table, not drawn, and counted in the subject "
             f"breakdown. {CI_NOTE}</p>")
    forest_csv("by-field", [(f"Subject: {a}", b, c) for a, b, c in subj_groups] +
               [(f"Registered group: {a}", b, c) for a, b, c in groups + [(FIELD_NAMES["?"], "", bf["?"])]])
    caption = (f"In every subject, {span} of citations to retracted papers still treat them as support. "
               f"Source: {SRC}, provisional.")
    return figure(
        "by-field", "Phase 2 census · is it one field's problem?",
        f"In every subject, {span} of citations to retracted papers still treat them as support.",
        f"From biology and medicine to the physical and social sciences, business and the humanities. Only "
        f"{pct(alo)} to {pct(ahi)} flag the paper as retracted or unreliable.",
        '<p class="sb-lead vz-detail">The registered grouping: each paper sorted by its whole set of subject codes</p>' + forest(groups), "",
        f"Source: {SRC}: {n(JUDGED)} citations from {POP}. Subjects as listed by Retraction Watch; the subject breakdown is a "
        f"later check, not in the registered plan.<span class=\"only-detail\"> Dot = estimate; line = 95% CI.</span> {PROVISIONAL}",
        table, caption,
        (f"{100 * low:.0f}–{100 * hi:.0f}%", "of citations to retracted papers still treat them as support, in every subject.", "s"),
        focus="s",
        simple=simple_bars("Treated it as support, by subject of the retracted paper",
                           [(sb[c]["name"], rt(sb[c]["substantive"]), "s", True) for c in sorder],
                           f"A paper can have more than one subject; its citations count under each. {sb[small]['name']} "
                           f"rests on {n(sb[small]['substantive']['n'])} citations, so it is the least certain."))


def reference_list():
    rs, ra = CENSUS["substantive_despite_ref_list_label"], CENSUS["aware_despite_ref_list_label"]
    rl = [r for r in J if r["ref_list_says_retracted"] == "True"]
    c = Counter(r["label"] for r in rl)
    check("reference list n", len(rl), rs["n"]); check("reference list support", c["substantive"], rs["k"])
    check("reference list flagged", c["aware"], ra["k"])
    check("2 in 5", abs(rt(rs) - 0.4) < 0.02, True)
    groups = [("Reference list says “retracted”", f"{n(rs['n'])} citations", {"substantive": rs, "aware": ra}),
              ("All citations", f"{n(JUDGED)} citations", {"substantive": S, "aware": A})]
    table = (ci_table(groups) + f"<p>“Reference list says retracted” means the word “retract” appears in the citing paper's own "
             f"reference entry for the work. Most entries carry a clear mark: a title prefix such as “RETRACTED:” (2,664) or a "
             f"retraction note (523). The other 441 mention it in other formats. On the 3,187 clear marks alone, 41.5% (1,322) cite "
             f"the work as support. The mark may come from the authors' reference software or from the journal. {CI_NOTE}</p>")
    forest_csv("reference-list", groups)
    caption = (f"Even when a paper's published reference list shows a cited study's retraction, {pct(rt(rs))} of those citations still "
               f"treat it as support. Source: {SRC}, provisional.")
    return figure(
        "reference-list", "Phase 2 census · was the warning on the page?",
        "2 in 5 citations still treat a retracted paper as support, even when the citing paper's published reference list shows the retraction.",
        f"That is {pct(rt(rs))} of {n(rs['n'])} such citations, about the same as for all citations ({pct(rt(S))}). "
        f"Only {pct(rt(ra))} flag it as retracted or unreliable in the text.",
        forest(groups, {"substantive": 0.6, "aware": 0.2}), "",
        f"Source: {SRC}: {n(JUDGED)} citations from {POP}.<span class=\"only-detail\"> Dot = estimate; line = 95% CI.</span> {PROVISIONAL}",
        table, caption,
        ("2 in 5", "citations still treat a retracted paper as support when the citing paper's published reference list shows the retraction.", "s"),
        simple=simple_bars("Treated it as support",
                           [("Reference list says “retracted”", rt(rs), "s", True), ("All citations", rt(S), "s", False)],
                           f"Only {pct(rt(ra))} of the marked citations flagged it as retracted or unreliable in the text."))



# ---------------------------------------------------------------- first citation-accuracy test (batch 6, 22 Oct 2026)
B6 = json.load(open(f"{ROOT}/data/stage3/batch6-result.json"))
B6_AS_OF = "22 Oct 2026"
B6_PILL = "Pending human review"
B6_SRC = "SaneCite citation-accuracy test (batch 6)"


def wilson(k, nn, z=1.959964):
    p = k / nn; d = 1 + z * z / nn; c = (p + z * z / (2 * nn)) / d
    h = z * (p * (1 - p) / nn + z * z / (4 * nn * nn)) ** 0.5 / d
    return [c - h, c + h]


def b6_by_type():
    t = B6["by_citation_type"]
    names = {"specific_claim": "Credits a specific finding", "background": "Background", "method_or_tool": "Method or tool"}
    st = {k: {"k": t[k]["major"], "n": t[k]["judged"], "ci95": wilson(t[k]["major"], t[k]["judged"])} for k in names}
    ref = B6["reference"]
    check("batch 6 judged", sum(t[k]["judged"] for k in t) + 21, B6["sample"]["judged"])  # 21 data-source citations
    check("batch 6 majors", sum(t[k]["major"] for k in t), ref["major"])
    spec, bg, mt = (st[k] for k in names)
    table = ("<table><tr><th>What the citation is used for</th><th>Judged</th><th>Badly misreport</th><th>Share (95% CI, %)</th><th>Any error</th></tr>"
             + "".join(f"<tr><td>{names[k]}</td><td>{t[k]['judged']}</td><td>{t[k]['major']}</td><td>{rc(st[k])}</td>"
                       f"<td>{t[k]['any_error']} ({pct(t[k]['any_error'] / t[k]['judged'])})</td></tr>" for k in names)
             + f"<tr><td>All judged (incl. 21 data-source citations)</td><td>{B6['sample']['judged']}</td><td>{ref['major']}</td>"
               f"<td>{pct(ref['major'] / B6['sample']['judged'])} ({ref['major_ci95'].replace('-', '–')})</td><td>{ref['any_error']} ({ref['any_error_rate']})</td></tr></table>"
             f"<p>{B6['sample']['pairs_drawn']:,} random citation pairs from {B6['sample']['population']}; {B6['sample']['judged']} could be judged. "
             "Answer key: two blind AI readers from different model families, disagreements settled by a third read. "
             "95% intervals are Wilson intervals.</p>")
    write_csv("stage3-by-type", ["citation_use", "judged", "badly_misreport", "share", "ci95_low", "ci95_high", "any_error"],
              [[names[k], t[k]["judged"], t[k]["major"], t[k]["major"] / t[k]["judged"], *st[k]["ci95"], t[k]["any_error"]] for k in names])
    caption = (f"Citations that credit a specific finding badly misreport the cited paper {pct(rt(spec))} of the time, against "
               f"{pct(rt(bg))} for background citations ({spec['k']} of {spec['n']} and {bg['k']} of {bg['n']}). "
               f"Source: {B6_SRC}, pending human review.")
    return figure(
        "stage3-by-type", "First accuracy test · which citations go wrong",
        f"{pct(rt(spec))} of citations that credit a specific finding badly misreport the paper they cite.",
        f"About 1 in {round(B6['sample']['judged'] / ref['major'])} citations overall ({pct(ref['major'] / B6['sample']['judged'])}). "
        f"Background citations: {pct(rt(bg))}. Methods and tools: {pct(rt(mt))}.",
        simple_bars("Badly misreport the cited paper, by what the citation is used for",
                    [(names["specific_claim"], rt(spec), "s", True), (names["background"], rt(bg), "s", False),
                     (names["method_or_tool"], rt(mt), "s", False)]),
        "Not in the test's plan; the same order held in an earlier, separate set of 500 citations (7.8%, 5.4%, 3.6%).",
        f"Source: {B6_SRC}: {B6['sample']['judged']} random citations from open-access PubMed Central papers, 2015–2025. "
        "Measured against AI readers, not people; pending human review.",
        table, caption,
        (pct(rt(spec)), "of citations that credit a specific finding badly misreport the paper they cite.", "s"),
        card_note="Not in the test's plan. The same order held in an earlier, separate set of 500 citations.",
        card_src=f"Source: {B6_SRC}, {B6['sample']['judged']} citations, {B6_AS_OF}, pending human review",
        as_of=B6_AS_OF, pill=B6_PILL)


PAGE_NOTES = {"stage3-by-type": (
    '<li><b>How it was read.</b><span>Two AI readers from different model families read each citation next to the paper it cites, '
    'without seeing each other\'s answers; a third read settled disagreements.</span></li>'
    '<li><b>What "badly misreport" means.</b><span>The cited paper does not say what the citation credits to it, says the opposite, '
    'or is about something else. Smaller errors, such as an overstated finding, are counted separately.</span></li>'
    '<li><b>What it covers.</b><span>Random citations from open-access research and review papers in PubMed Central, 2015 to 2025, '
    'where the cited paper is also open access.</span></li>'
    '<li><b>Check it yourself.</b><span><a href="/charts/stage3-by-type.csv">This chart\'s data</a> · '
    '<a href="/data/stage3/batch6-result.json">the full test result</a> · <a href="/checker.html#accuracy">how the test worked</a>.</span></li>')}

CHARTS = {"out-of-100": out_of_100(), "years-after": years_after(), "reference-list": reference_list(),
          "by-reason": by_reason(), "by-field": by_field(), "stage3-by-type": b6_by_type()}
TITLES = {cid: (f"{m['title'].rstrip('.')} | SaneCite", f"{m['sub']} Chart, data and caption, free to share.") for cid, m in META.items()}


def facts():
    """Key numbers as copy-ready lines for the press page. Phase 2 lines come from census.json;
    the Phase 1 line refreshes in the browser from results.json (data-r), like the home page."""
    br = CENSUS["by_reason_all"]; mis, err = br["misconduct, fabrication or duplication"], br["error or unreliable results"]
    early, late = CENSUS["by_years_after"]["1-2"]["substantive"], CENSUS["by_years_after"]["11+"]["substantive"]
    rs = CENSUS["substantive_despite_ref_list_label"]
    p2 = f"Phase 2 census, data as of {AS_OF}, pending human review."
    lines = [
        (f"{pct(rt(S))} of citations to retracted papers still treat them as support.",
         f"{n(S['k'])} of {n(JUDGED)} post-retraction citations (95% CI {ci(S)}). {CORR_NOTE} {p2}"),
        (f"Only {pct(rt(A))} of post-retraction citations flag the paper as retracted or unreliable.",
         f"{n(A['k'])} of {n(JUDGED)} citations (95% CI {ci(A)}), judged from the text around each citation. {p2}"),
        (f"More than ten years after a retraction, {pct(rt(late))} of citations still treat the paper as support.",
         f"{pct(rt(early))} in the first two years ({n(early['n'])} citations); {pct(rt(late))} after more than ten ({n(late['n'])}). {p2}"),
        (f"Citations to papers retracted for misconduct flag the problem {pct(rt(mis['aware']))} of the time, against "
         f"{pct(rt(err['aware']))} for error or unreliable results.",
         f"Both groups are cited as support about as often: {pct(rt(mis['substantive']))} and {pct(rt(err['substantive']))}. {p2}"),
        (f"2 in 5 citations still treat a retracted paper as support even when the citing paper's published reference list shows the retraction.",
         f"{n(rs['k'])} of {n(rs['n'])} citations ({pct(rt(rs))}, 95% CI {ci(rs)}). {p2}"),
    ]
    ref, sj = B6["reference"], B6["sample"]["judged"]
    spec = B6["by_citation_type"]["specific_claim"]
    p3 = "First citation-accuracy test, 22 Oct 2026, pending human review: measured against AI readers, not people."
    lines += [
        (f"About 1 in {round(sj / ref['major'])} citations badly misreport the paper they cite.",
         f"{ref['major']} of {sj} random citations from open-access PubMed Central papers ({ref['major_rate']}, 95% CI {ref['major_ci95'].replace('-', '–')}); "
         f"{ref['any_error_rate']} have some error. {p3}"),
        (f"Citations that credit a specific finding badly misreport it {pct(spec['major'] / spec['judged'])} of the time.",
         f"{spec['major']} of {spec['judged']}, against {pct(B6['by_citation_type']['background']['major'] / B6['by_citation_type']['background']['judged'])} "
         f"for background citations. Not in the test's plan; the same order held in an earlier set of 500. {p3}"),
    ]
    items = "".join(f'<li><span>{esc(a)}<small>{esc(b)}</small></span><button type="button" class="vz-btn" data-copy-li>Copy</button></li>'
                    for a, b in lines)
    r1 = json.load(open(f"{ROOT}/results.json"))
    items += ('<li><span>Nearly two-thirds of retracted papers were cited again after the retraction.<small>Phase 1 count: '
              f'<span data-r="cited_after_retraction">{n(r1["cited_after_retraction"])}</span> of '
              f'<span data-r="checks_resolved">{n(r1["checks_resolved"])}</span> retracted papers with a DOI (retracted 2024 or earlier, '
              f'found in OpenAlex), <span data-r="post_retraction_citations">{n(r1["post_retraction_citations"])}</span> citations in all, '
              f'paperwork retractions left out. Last updated <span data-r="updated">'
              f'{datetime.datetime.fromisoformat(r1["updated"].replace("Z", "+00:00")):%d %b %Y, %H:%M} UTC</span>.</small></span><button type="button" class="vz-btn" data-copy-li>Copy</button></li>')
    return f'<ul class="facts">{items}</ul>'


def fill(body):
    """Replace <!--chart:NAME--> markers in a page body with the chart, and <!--charts:facts--> with the key numbers."""
    for cid, fig in CHARTS.items():
        body = body.replace(f"<!--chart:{cid}-->", fig)
    if "<!--charts:facts-->" in body:
        body = body.replace("<!--charts:facts-->", facts())
    return body
