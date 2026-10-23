#!/usr/bin/env python3
"""Stage the Lists and the citation-accuracy checker into this repository: code, data, records and README files.

usage: stage_release.py [--sources FILE]

Rebuilds two folders from the current working copies, so nothing here is copied by hand and goes stale:
  lists/    the code that builds the named Lists (ranking, second reading, author matching, corrections) and the
            site's lists.py and charts.py, plus the Lists data (the published CSV files and their inputs)
  checker/  the stage-3 accuracy test of the citation checker: protocol, pre-registrations, deviations, the hash log,
            the scripts, the reference reads and items.csv (one row per drawn citation, every verdict and vote)

Run it again on the day of a release. It deletes and rewrites only lists/ and checker/.

Where the working copies live is private and stays out of the repository: the sources file (default
.stage_sources.json at the repository root, listed in .gitignore) maps each source name to its folder, plus
"rewrite": prefixes of private folder paths that the staged code mentions, each with the neutral name that replaces
it (for example work/top10/). The replacement is plain text substitution; SOURCES.sha256 in each folder gives the
hash of every file before and after it, and records that carry a registered hash (the checker's PREREG_HASHES.txt)
are copied byte for byte.

What is never staged: letters, correspondence and reply e-mails (only the published replies.csv summary is),
e-mail addresses other than the project address, the full text of citing or cited papers (sample files and reading
packets), raw model outputs with quoted passages, and any passage from a text-mining-licensed author manuscript
(PROTOCOL.md amendment 11). The script stops if a staged file breaks one of these rules.
"""
import argparse, csv, hashlib, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lists code, by source folder. Letter builders, recipient lists and send scripts are left out on purpose.
LISTS_CODE = {
    "top10": ["rank.py", "packets.py", "packets2.py", "mkv2.py", "lists_data.py", "author_items.py", "fetch_authors.py",
              "status_all.py", "crossref_check.py"],
    "listfix": ["make_corrections.py", "sync_lists_json.py", "ruling.py", "works.py", "works2.py", "notices.py",
                "fetch7.py", "fields_counts.py", "fields_huang.py", "fields_reasons.py", "reset_fields.py", "scrub.py",
                "facts.py"],
    "corrections": ["apply_corrections.py", "add_recounts.py", "citing_dates.py", "lifesci_notices.py",
                    "notice_dates.py", "pmc_dates.py"],
}
LISTS_READINGS = ["verdicts_papers.jsonl", "verdicts_journals.jsonl", "verdicts_authors.jsonl",
                  "verdicts2_papers.jsonl", "verdicts2_authors.jsonl"]   # second-reading verdicts (no passages)
SITE_CODE = ["tools/lists.py", "tools/charts.py"]
SITE_DATA = ["data/phase2/lists.json", "data/phase2/list_corrections.json", "data/phase2/list_checks.csv",
             "data/phase2/author_items.json", "data/phase2/retraction_status.csv", "data/phase2/by_subject.json",
             "data/phase2/paper_subjects.csv"]
CHECKER_RECORDS = ["PROTOCOL.md", "PREREG_RERUN_2026-10-22.md", "PREREG_SYSTEM_2026-10-22.md",
                   "PREREG_CLEF_SCREEN_2026-10-22.md", "PROTOCOL_TUNING_2026-10-22.md", "METHOD_CHOSEN_2026-10-22.md",
                   "METHOD_CHOSEN_v2_2026-10-22.md", "METHOD_CHOSEN_v3_2026-10-22.md", "MODEL_CARDS_2026-10-22.md",
                   "model-cards/configs.json", "DEVIATIONS.md", "PREREG_HASHES.txt", "SYSTEM_LOCKED_2026-10-22.json",
                   "B6_RESULT_2026-10-22.json", "B6_RESULT_2026-10-22.md", "TUNING_RESULTS_2026-10-22.md", "RESULTS.md",
                   "run.sh", "run_batch.sh"]
CHECKER_READS = ["batches/b6/gold/gold.jsonl", "batches/b6/gold/adjudicated.jsonl", "batches/b6/ref_A/readerA.jsonl",
                 "batches/b6/ref_muse/muse.jsonl", "batches/b6/ref_grok_or.jsonl", "batches/b6/ref_gemini.jsonl",
                 "batches/b6/gold_gemini/gold.jsonl", "batches/b6/draws_test.json", "batches/b6/draws_flagged.json"]
SKIP_SCRIPT = re.compile(r"(\.bak|\.v\d+$|\.mjs$|^site_shot|^grants\.py$)")   # backups, screenshot helpers, grant drafts
TEXT = (".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".sh")

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ALLOWED_EMAIL = {"hi@saneapps.com"}
FORBIDDEN = [re.compile(p) for p in (r"/Users/", r"stephansmac", r"\bsk-[A-Za-z0-9]{16,}", r"Bearer [A-Za-z0-9._-]{20,}",
                                     r"CORRESPONDENCE\.md")]
WARN = re.compile(r"(\b(?:Mac Mini|the Mini|Mini clock|Spark|subagents?)\b|SaneApps/(?:outputs|websites|clients|infra))")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


class Stager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rewrite = sorted(cfg.get("rewrite", {}).items(), key=lambda kv: -len(kv[0]))
        self.log = {}   # folder -> [(original sha, staged sha, staged path, source name)]
        self.warnings = []

    def src(self, name, rel=""):
        return os.path.join(os.path.expanduser(self.cfg[name]), rel)

    def put(self, folder, src, dest, verbatim=False):
        out = os.path.join(ROOT, folder, dest)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if verbatim or not src.endswith(TEXT):
            shutil.copyfile(src, out)
        else:
            s = open(src, encoding="utf-8").read()
            for old, new in self.rewrite: s = s.replace(old, new)
            open(out, "w", encoding="utf-8").write(s)
        self.log.setdefault(folder, []).append((sha(src), sha(out), dest))

    def write(self, folder, dest, text):
        out = os.path.join(ROOT, folder, dest)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(text)


def git_state(path):
    try:
        head = subprocess.run(["git", "-C", path, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", path, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        return head + (" (with uncommitted changes)" if dirty else "")
    except OSError:
        return "unknown"


def checker_items(st):
    """One row per drawn citation of batch 6: identifiers, both readers, the reference, and the locked system's votes."""
    base = st.src("checker")
    sys.path.insert(0, os.path.join(base, "scripts"))
    import score_b6, score_v3   # the registered scorer; reused so the table matches B6_RESULT exactly
    lock = json.load(open(os.path.join(base, "SYSTEM_LOCKED_2026-10-22.json")))
    run = os.path.join(base, "runs", "b6")
    jl = lambda p: [json.loads(l) for l in open(os.path.join(base, p)) if l.strip()]
    meta = {str(r["draw"]): r for r in jl("batches/b6/sample.jsonl") if r.get("status") == "ok"}
    a = {str(r["draw"]): r for r in jl("batches/b6/ref_A/readerA.jsonl")}
    b = {str(r["draw"]): (r.get("parsed") or {}) for r in jl("batches/b6/ref_muse/muse.jsonl")}
    gold = {str(r["draw"]): r for r in jl("batches/b6/gold/gold.jsonl")}
    calls, flagged, _ = score_b6.system_calls(run, lock["primary"])
    calls2, flagged2, _ = score_b6.system_calls(run, lock["secondary"])
    arms = {x: score_v3.load_arm(run, "b6", x)[0] for x in ["clef", "jev"] + lock["primary"]["deciders"]}
    rows = []
    for d in sorted(gold, key=int):
        m, g = meta.get(d, {}), gold[d]
        key = d if d in calls else int(d) if int(d) in calls else d
        vote = lambda x: (arms[x].get(key) or arms[x].get(d) or (None, None))
        rows.append({"draw": d, "citing_pmcid": m.get("citing_pmcid"), "citing_year": m.get("year"),
                     "citing_article_type": m.get("article_type"), "cited_pmid": m.get("cited_pmid"),
                     "cited_pmcid": m.get("cited_pmcid"), "cited_year": m.get("cited_year"),
                     "reader_a": (a.get(d) or {}).get("verdict"), "reader_a_model": (a.get(d) or {}).get("reader"),
                     "reader_b": b.get(d, {}).get("verdict"), "reader_b_model": "muse",
                     "reference": g["verdict"], "reference_source": g.get("source"), "citation_type": g.get("citation_type"),
                     "screen_clef_p_major": vote("clef")[0], "screen_jev_p_major": vote("jev")[0],
                     **{f"vote_{x}": vote(x)[1] for x in lock["primary"]["deciders"]},
                     "flagged_primary": key in flagged, "system_primary": calls.get(key),
                     "flagged_secondary": key in flagged2, "system_secondary": calls2.get(key)})
    sys.path.pop(0)
    out = os.path.join(ROOT, "checker", "items.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    st.log.setdefault("checker", []).append(("(built)", sha(out), "items.csv"))
    return rows


def scan(folder, st):
    bad = []
    for dp, _, fn in os.walk(os.path.join(ROOT, folder)):
        for x in fn:
            p = os.path.join(dp, x); rel = os.path.relpath(p, ROOT)
            if not x.endswith(TEXT): continue
            s = open(p, encoding="utf-8", errors="ignore").read()
            for e in set(EMAIL.findall(s)) - ALLOWED_EMAIL:
                if not re.search(r"@(cf|hf)/", e): bad.append(f"{rel}: e-mail address {e}")
            for rx in FORBIDDEN:
                if rx.search(s): bad.append(f"{rel}: matches {rx.pattern}")
            for w in sorted(set(WARN.findall(s))): st.warnings.append(f"{rel}: mentions '{w}'")
    return bad


README_LISTS = """# Lists: code and data

The named Lists on sanecite.com (retracted papers, journals and authors whose papers cite retracted work as support),
with the code that builds them. Staged by `scripts/stage_release.py` on {date} from the site at {site_state}.

| Path | What it is |
|---|---|
| `code/rank.py`, `code/packets*.py`, `code/mkv2.py` | Candidate ranking from the census and the second-reading packets and verdicts |
| `code/lists_data.py`, `code/author_items.py` | Builds `lists.json`, `list_checks.csv`, `retraction_status.csv` and the author items |
| `code/fetch_authors.py`, `code/status_all.py`, `code/crossref_check.py` | Author matching by ORCID iD; retraction status from PubMed and Crossref |
| `code/listfix/` | Corrections of 21 Oct 2026: notices, reason rulings, fields, sync into `lists.json` |
| `code/corrections/` | Corrections of 22 Oct 2026: notice and first-online dates, recounts |
| `code/site/lists.py`, `code/site/charts.py` | The site code that turns the data into the Lists page and its CSV files |
| `readings/` | Second-reading verdicts (one line per citation read, with a one-sentence reason) |
| `data/` | The inputs the page is built from (`lists.json`, `list_corrections.json`, `list_checks.csv`, ...) |
| `csv/` | The CSV files the page offers for download, as published |
{method_row}
Code is under the MIT license (`../LICENSE`); SaneCite-made data under CC BY 4.0 (`../LICENSE-DATA`).
`SOURCES.sha256` lists each file's hash before and after staging. Paths to private working folders in the code were
replaced by `work/<name>/`; nothing else was changed. Letters to authors and the replies themselves are not published;
`csv/replies.csv` is the published summary of each reply under the right-of-reply rule.
"""

README_CHECKER = """# Checker: the citation-accuracy test (batch 6)

The test of 996 random citations behind the accuracy figures on sanecite.com/checker, as recorded. Staged by
`scripts/stage_release.py` on {date}.

| Path | What it is |
|---|---|
| `records/PROTOCOL.md`, `records/PREREG_*.md` | The test plan and the pre-registrations, with their dated amendments |
| `records/DEVIATIONS.md` | Every departure from the plan |
| `records/PREREG_HASHES.txt` | The hash log. It says itself which hashes were recorded after the fact and that amendments 1-6 to the rerun plan were made without a hash each |
| `records/SYSTEM_LOCKED_2026-10-22.json` | The checker as locked before any model call on batch 6 |
| `records/B6_RESULT_2026-10-22.*` | The scored result |
| `reads/` | The reference reads: reader A, reader B, the adjudicated items and the final reference (`gold.jsonl`) |
| `items.csv` | One row per citation: identifiers, both readers, the reference, the screen scores, each decider's vote and the system's call |
| `scripts/` | The sampling, reading, scoring and locking scripts |

Hashed records and reads are copied byte for byte, so `shasum -a 256` on them matches `PREREG_HASHES.txt` where the
log lists them (paths in the log are relative to the original working folder). Scripts had private folder paths
replaced by `work/<name>/`; `SOURCES.sha256` gives each file's hash before and after. The citing and cited passages
the readers saw are not included (they are other authors' text); `items.csv` gives the PMC and PubMed IDs to find them.
All reads are by AI models; no human has checked them yet. Code MIT, data CC BY 4.0 (see the repository root).
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=os.path.join(ROOT, ".stage_sources.json"))
    a = ap.parse_args()
    if not os.path.exists(a.sources):
        sys.exit(f"no sources file at {a.sources}: it maps top10, listfix, corrections, site, checker (and optional "
                 "lists_method) to their folders, plus 'rewrite' prefixes")
    st = Stager(json.load(open(a.sources)))
    import datetime
    date = datetime.date.today().isoformat()
    for folder in ("lists", "checker"):
        p = os.path.join(ROOT, folder)
        if os.path.isdir(p): shutil.rmtree(p)   # both folders belong to this script alone

    for name, files in LISTS_CODE.items():
        sub = "" if name == "top10" else name + "/"
        for f in files: st.put("lists", st.src(name, f), f"code/{sub}{f}")
    for f in LISTS_READINGS: st.put("lists", st.src("top10", f), f"readings/{f}")
    for f in SITE_CODE: st.put("lists", st.src("site", f), "code/site/" + os.path.basename(f))
    for f in SITE_DATA: st.put("lists", st.src("site", f), "data/" + os.path.basename(f))
    for f in sorted(os.listdir(st.src("site", "lists"))):
        if f.endswith((".csv", ".md")): st.put("lists", st.src("site", "lists/" + f), "csv/" + f)
    method = os.path.expanduser(st.cfg.get("lists_method", ""))
    method_row = ""
    if method and os.path.exists(method):
        st.put("lists", method, "METHOD.md"); method_row = "| `METHOD.md` | How the Lists are made, step by step |\n"
    st.write("lists", "README.md", README_LISTS.format(date=date, site_state=git_state(st.src("site")), method_row=method_row))

    for f in CHECKER_RECORDS:
        if os.path.exists(st.src("checker", f)): st.put("checker", st.src("checker", f), "records/" + f, verbatim=True)
    for f in CHECKER_READS:
        dest = "reads/" + f.replace("batches/b6/", "").replace("/", "_")
        st.put("checker", st.src("checker", f), dest, verbatim=True)
    for f in sorted(os.listdir(st.src("checker", "scripts"))):
        if f.endswith(".py") and not SKIP_SCRIPT.search(f): st.put("checker", st.src("checker", "scripts/" + f), "scripts/" + f)
    rows = checker_items(st)
    st.write("checker", "README.md", README_CHECKER.format(date=date))

    for folder, entries in st.log.items():
        lines = [f"# {folder}/ staged {date}: sha256 of the source file, sha256 of the staged file, staged path",
                 "# The two hashes differ only where private folder paths were replaced (see README.md)."]
        lines += [f"{o}  {s}  {p}" for o, s, p in entries]
        st.write(folder, "SOURCES.sha256", "\n".join(lines) + "\n")
    bad = scan("lists", st) + scan("checker", st)
    for w in st.warnings: print("note:", w)
    if bad:
        print("\n".join("STOP: " + b for b in bad)); sys.exit(1)
    n = {f: len(e) for f, e in st.log.items()}
    print(f"staged lists/ ({n.get('lists', 0)} files) and checker/ ({n.get('checker', 0)} files, items.csv {len(rows)} rows)")


if __name__ == "__main__":
    main()
