#!/usr/bin/env python3
"""Stage the Lists and the citation-accuracy checker into this repository: code, data, records and README files.

usage: stage_release.py [--sources FILE]      stage lists/ and checker/ (release branch only, on release day)
       stage_release.py --scan-repo           scan every tracked file with the same rules; changes nothing

Rebuilds two folders from the current working copies, so nothing here is copied by hand and goes stale:
  lists/    the code that builds the named Lists (ranking, second reading, author matching, corrections) and the
            site's lists.py and charts.py, plus the Lists data (the published CSV files and their inputs)
  checker/  the stage-3 accuracy test of the citation checker: protocol, pre-registrations, deviations, the hash log,
            the scripts, the reference reads and items.csv (one row per drawn citation, every verdict and vote)

The Lists name people, so lists/ and checker/ are committed only on the release branch and merged on launch day,
after the reply deadline (SOP H). The sequence for that day: run this script, then
python3 scripts/verify_manifest.py --update "<release>", then python3 scripts/stage_release.py --scan-repo, then push.

Everything is staged into a temporary folder and scanned there; lists/ and checker/ are replaced only when the scan
is clean, so a stopped run leaves the repository as it was.

Where the working copies live is private and stays out of the repository: the sources file (default
.stage_sources.json at the repository root, listed in .gitignore) maps each source name to its folder, plus
  "rewrite":      prefixes of private folder paths (and other private phrases) in staged files, each with the neutral
                  text that replaces it (for example work/top10/);
  "rewrite_code": the same, applied to code only (.py, .sh), so data stays as the site serves it;
  "redact":       {record path: [[old, new, why], ...]} for records that are otherwise copied byte for byte. Each
                  old text must still be in the record, or the run stops. README.md names every redacted record and
                  why; SOURCES.sha256 keeps the hash of the original, which can be shown on request;
  "stop_strings": private literals (such as an account ID) that must never be staged;
  "allow":        {staged path: [rule, ...]} for a rule below that a file may break, each with a reason.
The rewrite is plain text substitution; SOURCES.sha256 in each folder gives the hash of every file before and after.

What is never staged, and the scan stops on it:
  - e-mail addresses other than the project address; private paths, machine and agent names, internal tool and
    procedure names, account IDs and keys;
  - letters, correspondence and reply e-mails (only the published replies.csv summary is);
  - a held entry: any "pending_entries" key in the Lists data, or any id from the site's tools/held.json outside the
    census-wide files (SOP H2);
  - quoted passages from the citing or cited papers: a "quote" field anywhere in the reads is dropped when staged,
    and the scan stops if one is left;
  - the full text of citing or cited papers (sample files and reading packets), and any passage from a
    text-mining-licensed author manuscript (PROTOCOL.md amendment 11).
A record copied byte for byte must also match the latest hash its own hash log (PREREG_HASHES.txt) lists for it.
"""
import argparse, csv, gzip, hashlib, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGED = ("lists", "checker", "stories")

# Lists code, by source folder. Letter builders, recipient lists and send scripts are left out on purpose.
LISTS_CODE = {
    "top10": ["rank.py", "packets.py", "packets2.py", "mkv2.py", "lists_data.py", "author_items.py", "fetch_authors.py",
              "status_all.py", "crossref_check.py"],
    "listfix": ["make_corrections.py", "sync_lists_json.py", "ruling.py", "works.py", "works2.py", "notices.py",
                "fetch7.py", "fields_counts.py", "fields_huang.py", "fields_reasons.py", "reset_fields.py", "facts.py"],
                # scrub.py is left out: an internal tidy-up check whose pattern list names people and internal tools
    "corrections": ["apply_corrections.py", "add_recounts.py", "citing_dates.py", "lifesci_notices.py",
                    "notice_dates.py", "pmc_dates.py"],
}
LISTS_READINGS = ["verdicts_papers.jsonl", "verdicts_journals.jsonl", "verdicts_authors.jsonl",
                  "verdicts2_papers.jsonl", "verdicts2_authors.jsonl"]   # second-reading verdicts (no passages)
SITE_CODE = ["tools/lists.py", "tools/charts.py"]
SITE_DATA = ["data/phase2/lists.json", "data/phase2/list_corrections.json", "data/phase2/list_checks.csv",
             "data/phase2/author_items.json", "data/phase2/retraction_status.csv", "data/phase2/by_subject.json",
             "data/phase2/paper_subjects.csv"]
SITE_HELD = "tools/held.json"   # private on the site; entries held until their authors have been written to
CENSUS_WIDE = ("lists/data/retraction_status.csv", "lists/data/paper_subjects.csv")   # every paper, unranked (site rule)
CHECKER_RECORDS = ["PROTOCOL.md", "PREREG_RERUN_2026-10-22.md", "PREREG_SYSTEM_2026-10-22.md",
                   "PREREG_CLEF_SCREEN_2026-10-22.md", "PROTOCOL_TUNING_2026-10-22.md", "METHOD_CHOSEN_2026-10-22.md",
                   "METHOD_CHOSEN_v2_2026-10-22.md", "METHOD_CHOSEN_v3_2026-10-22.md", "MODEL_CARDS_2026-10-22.md",
                   "model-cards/configs.json", "DEVIATIONS.md", "PREREG_HASHES.txt", "SYSTEM_LOCKED_2026-10-22.json",
                   "B6_RESULT_2026-10-22.json", "B6_RESULT_2026-10-22.md", "TUNING_RESULTS_2026-10-22.md", "RESULTS.md",
                   "run.sh", "run_batch.sh"]
CHECKER_READS = ["batches/b6/gold/gold.jsonl", "batches/b6/gold/adjudicated.jsonl", "batches/b6/ref_A/readerA.jsonl",
                 "batches/b6/ref_muse/muse.jsonl", "batches/b6/ref_grok_or.jsonl", "batches/b6/ref_gemini.jsonl",
                 "batches/b6/gold_gemini/gold.jsonl", "batches/b6/draws_test.json", "batches/b6/draws_flagged.json"]
# Story re-analyses on sanecite.com/stories (added 27 Oct 2026). Code and the trial-registry sweep only: the papers'
# full texts and figures beside them in the working folder are never staged.
STORIES_FILES = ["meta.py", "vitc/rerun.py", "syn/rerun_sildenafil.py", "syn/rerun_dhea.py", "ctgov_sweep.py",
                 "ctgov_hits.jsonl", "ctgov_after.json"]
HASH_LOG = "PREREG_HASHES.txt"
QUOTE_KEYS = {"quote"}   # quoted passages from the papers; quote_found (a yes/no) stays
SKIP_SCRIPT = re.compile(r"(\.bak|\.v\d+$|\.mjs$|^site_shot|^grants\.py$)")   # backups, screenshot helpers, grant drafts
TEXT = (".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".sh", ".cff", ".tsv", ".yml", ".yaml", ".toml")

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ALLOWED_EMAIL = {"hi@saneapps.com"}
# Rules by name. "hard" rules apply to every file, data included; "inhouse" rules apply to code and documents (data
# files hold other authors' text, where "Spark" or "the Mini" (-Mental State) are ordinary words).
HARD = {"private path": r"/Users/|stephansmac", "api key": r"\bsk-[A-Za-z0-9]{16,}|Bearer [A-Za-z0-9._-]{20,}",
        "correspondence": r"CORRESPONDENCE\.md", "account id": r"ACCOUNT_ID\S*?[0-9a-f]{32}"}
INHOUSE = {"machine name": r"\bMac Mini\b|\bthe Mini\b|\bMini clock\b|\(Air[;)]", "agent name": r"\bSpark\b|\bsubagents?\b",
           "private folder": r"SaneApps/(?:outputs|websites|clients|infra)|\bSaneProcess\b",
           "secret store": r"\bsane-env\b", "internal procedure": r"\bSOP C\d+"}
RULES = {k: re.compile(v) for k, v in {**HARD, **INHOUSE}.items()}
DATA_EXT = (".jsonl", ".gz", ".csv", ".tsv")
# Repository files that may break a rule, each with the reason. Staged files get theirs from the sources file.
REPO_ALLOW = {
    "PROTOCOL.md": {"agent name": "registered amendment text, published 16 Oct 2026; quoted as registered"},
    "errata/epmc_titles.jsonl.gz": {"e-mail": "article titles exactly as Europe PMC returns them (one title has an "
                                              "author's address in it)"},
    "scripts/stage_release.py": {"*": "this file defines the rules"},
    "lists/data/list_corrections.json": {"internal procedure": "kept as the site serves it (its replies_rule names "
                                                               "the rule SOP C9); same allow as the staging step"},
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def read_text(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f: return f.read()
    return open(path, encoding="utf-8", errors="ignore").read()


def check_text(rel, s, allow, extra=()):
    """Rule breaks in one file's text, as 'path: rule (match)' lines. allow: {rule or '*' or 'e-mail': reason}."""
    if "*" in allow: return []
    bad = []
    if "e-mail" not in allow:
        for e in sorted(set(EMAIL.findall(s)) - ALLOWED_EMAIL):
            if not re.search(r"@(cf|hf)/", e): bad.append(f"{rel}: e-mail address {e}")
    data = rel.endswith(DATA_EXT)
    for name, rx in RULES.items():
        if name in allow or (data and name in INHOUSE): continue
        m = rx.search(s)
        if m: bad.append(f"{rel}: {name} ({m.group(0)!r})")
    for lit in extra:
        if lit and lit in s: bad.append(f"{rel}: private string from the sources file")
    return bad


def keys_in(o, names):
    if isinstance(o, dict):
        return any(k in names or keys_in(v, names) for k, v in o.items())
    if isinstance(o, list):
        return any(keys_in(v, names) for v in o)
    return False


def drop_keys(o, names):
    if isinstance(o, dict): return {k: drop_keys(v, names) for k, v in o.items() if k not in names}
    if isinstance(o, list): return [drop_keys(v, names) for v in o]
    return o


def json_docs(path):
    s = open(path, encoding="utf-8").read()
    if path.endswith(".jsonl"): return [json.loads(l) for l in s.split("\n") if l.strip()]
    return [json.loads(s)]


def hash_log(path):
    """Latest hash per path in a PREREG_HASHES.txt-style log ('[time] <sha256>  <path>  (comment)')."""
    latest = {}
    for l in open(path, encoding="utf-8"):
        m = re.match(r"^(?:\S*Z\s+)?([0-9a-f]{64})\s+(\S+)", l)
        if m: latest[m.group(2)] = m.group(1)
    return latest


class Stager:
    def __init__(self, cfg, base):
        self.cfg, self.base = cfg, base
        self.rewrite = sorted(cfg.get("rewrite", {}).items(), key=lambda kv: -len(kv[0]))
        self.rewrite_code = sorted(cfg.get("rewrite_code", {}).items(), key=lambda kv: -len(kv[0]))
        self.redact = cfg.get("redact", {})
        self.log = {}        # folder -> [(original sha, staged sha, staged path)]
        self.problems = []   # reasons to stop
        self.redacted = []   # (staged path, why)
        self.verbatim = []   # (source path, source rel, staged path) of records copied byte for byte

    def src(self, name, rel=""):
        return os.path.join(os.path.expanduser(self.cfg[name]), rel)

    def out(self, folder, dest):
        p = os.path.join(self.base, folder, dest)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def put(self, folder, src, dest, verbatim=False, rel=None, strip=None):
        out = self.out(folder, dest)
        staged = f"{folder}/{dest}"
        if strip:   # drop quoted passages; one JSON document per line, as in the source
            docs = [drop_keys(d, strip) for d in json_docs(src)]
            with open(out, "w", encoding="utf-8") as f:
                if src.endswith(".jsonl"): f.writelines(json.dumps(d, ensure_ascii=False) + "\n" for d in docs)
                else: json.dump(docs[0], f, ensure_ascii=False)
            self.redacted.append((staged, "the quoted passages from the papers (\"quote\" fields) are left out"))
        elif verbatim:
            fixes = self.redact.get(staged, [])
            if not fixes:
                shutil.copyfile(src, out)
                if rel: self.verbatim.append((src, rel, staged))
            else:
                s = open(src, encoding="utf-8").read()
                for old, new, why in fixes:
                    if old not in s: self.problems.append(f"{staged}: redaction text no longer in the record ({why})")
                    s = s.replace(old, new)
                open(out, "w", encoding="utf-8").write(s)
                self.redacted.append((staged, "; ".join(sorted({w for _, _, w in fixes}))))
                if rel: self.verbatim.append((src, rel, staged))   # the original must still match the log
        elif not src.endswith(TEXT):
            shutil.copyfile(src, out)
        else:
            s = open(src, encoding="utf-8").read()
            for old, new in self.rewrite: s = s.replace(old, new)
            if src.endswith((".py", ".sh")):
                for old, new in self.rewrite_code: s = s.replace(old, new)
            open(out, "w", encoding="utf-8").write(s)
        self.log.setdefault(folder, []).append((sha(src), sha(out), dest))

    def write(self, folder, dest, text):
        open(self.out(folder, dest), "w", encoding="utf-8").write(text)


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
    out = st.out("checker", "items.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    st.log.setdefault("checker", []).append(("(built)", sha(out), "items.csv"))
    return rows


def held_ids(st):
    p = st.src("site", SITE_HELD)
    if not os.path.exists(p): return set()
    return {str(x["entry"]) for x in json.load(open(p)).get("pending_entries", [])}


def scan_staged(st):
    """Every rule over the staged folders, before anything replaces lists/ or checker/."""
    bad = list(st.problems)
    allow_cfg = st.cfg.get("allow", {})
    held = held_ids(st)
    for folder in STAGED:
        for dp, _, fn in os.walk(os.path.join(st.base, folder)):
            for x in fn:
                p = os.path.join(dp, x); rel = os.path.relpath(p, st.base)
                if not x.endswith(TEXT): continue
                s = read_text(p)
                bad += check_text(rel, s, allow_cfg.get(rel, {}), st.cfg.get("stop_strings", []))
                if rel.startswith("lists/") and rel not in CENSUS_WIDE:
                    hits = sorted(e for e in held if re.search(rf"(?<!\d){re.escape(e)}(?!\d)", s))
                    if hits: bad.append(f"{rel}: names a held entry {hits} (tools/held.json; SOP H2)")
                if x.endswith((".json", ".jsonl")):
                    try: docs = json_docs(p)
                    except ValueError: bad.append(f"{rel}: not valid JSON"); continue
                    if rel.startswith("lists/") and keys_in(docs, {"pending_entries"}):
                        bad.append(f"{rel}: has a pending_entries key; held entries stay out of every published file (SOP H2)")
                    if (rel.startswith("checker/reads/") or rel.startswith("lists/readings/")) and \
                            "quote" not in allow_cfg.get(rel, {}) and keys_in(docs, QUOTE_KEYS):
                        bad.append(f"{rel}: has a quoted passage (\"quote\" field)")
    log = os.path.join(st.src("checker"), HASH_LOG)
    latest = hash_log(log) if os.path.exists(log) else {}
    for src, rel, staged in st.verbatim:
        want = latest.get(rel) or next((h for pth, h in latest.items() if rel.endswith("/" + pth)), None)
        if want and sha(src) != want:
            bad.append(f"{staged}: source does not match its latest hash in {HASH_LOG} (add a dated line, recorded "
                       f"after the fact, before staging)")
    return bad


def scan_repo():
    """Every tracked file of the repository, with the same rules (hard rules only for data files)."""
    files = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    bad = []
    for rel in files:
        p = os.path.join(ROOT, rel)
        if not rel or not os.path.isfile(p): continue
        if not (rel.endswith(TEXT + (".gz",)) or rel in ("LICENSE", "LICENSE-DATA", ".gitignore")): continue
        bad += check_text(rel, read_text(p), REPO_ALLOW.get(rel, {}))
        if rel.startswith("lists/") and rel.endswith((".json", ".jsonl")) and keys_in(json_docs(p), {"pending_entries"}):
            bad.append(f"{rel}: has a pending_entries key (SOP H2)")
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

README_STORIES = """# Stories: the re-analyses behind sanecite.com/stories

Code and data for the case stories published on sanecite.com/stories on 29 October 2026. Staged by
`scripts/stage_release.py` on {date}. The papers' full texts and figures we read are not included; each story links them.

| Path | What it is |
|---|---|
| `meta.py` | Small meta-analysis helpers matching RevMan: Mantel-Haenszel fixed and DerSimonian-Laird random risk ratios, inverse-variance mean differences |
| `vitc/rerun.py` | The sepsis guideline story: re-runs the vitamin C meta-analyses with and without the retracted trial (risk ratios for mortality; Hedges' g with DerSimonian-Laird random effects for the vasoactive-drug outcome) |
| `syn/rerun_sildenafil.py`, `syn/rerun_dhea.py` | Re-runs of two reviews' pooled estimates with and without the retracted trial (BMC Pediatrics 2024, sildenafil; J Ovarian Res 2025, DHEA) |
| `ctgov_sweep.py` | Searches ClinicalTrials.gov for registered trials that cite a retracted paper in the census |
| `ctgov_hits.jsonl` | Everything the sweep found: 646 pairs of a registered trial and a retracted paper it lists |
| `ctgov_after.json` | The 224 pairs from `ctgov_hits.jsonl` where the trial was first submitted after the retraction, leaving out retract-and-replace notices |

Each script prints its numbers; run it with Python 3 from this folder (`ctgov_sweep.py` expects the census
`data/stage1_papers.jsonl` one folder up and calls the ClinicalTrials.gov API).
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

Records and reads are copied byte for byte unless listed below, so `shasum -a 256` on them matches the latest hash
`PREREG_HASHES.txt` gives for them (paths in the log are relative to the original working folder). Some hashes in the
log were recorded after the fact, and the log says so on those lines: amendment 6 to `PREREG_SYSTEM_2026-10-22.md`
(23 Oct 2026, the decision to publish the batch 6 result marked "pending human review") was written after the result
was known and hashed the next day. Scripts had private folder paths replaced by `work/<name>/`; `SOURCES.sha256` gives
each file's hash before and after. The citing and cited passages the readers saw are not included (they are other
authors' text); `items.csv` gives the PMC and PubMed IDs to find them.
{changed}
All reads are by AI models; no human has checked them yet. Code MIT, data CC BY 4.0 (see the repository root).
"""


def changed_section(redacted):
    if not redacted: return ""
    lines = ["", "Files that differ from the original, and why (the original's hash is in `SOURCES.sha256`; the",
             "originals can be shown on request):", ""]
    lines += [f"- `{p.split('/', 1)[1]}`: {why}" for p, why in sorted(redacted) if p.startswith("checker/")]
    return "\n".join(lines) + "\n"


def stage(cfg):
    import datetime
    date = datetime.date.today().isoformat()
    base = tempfile.mkdtemp(prefix=".stage-", dir=ROOT)   # same disk as the repository, so the swap is a rename
    try:
        st = Stager(cfg, base)
        for name, files in LISTS_CODE.items():
            sub = "" if name == "top10" else name + "/"
            for f in files: st.put("lists", st.src(name, f), f"code/{sub}{f}")
        for f in LISTS_READINGS: st.put("lists", st.src("top10", f), f"readings/{f}")
        for f in SITE_CODE: st.put("lists", st.src("site", f), "code/site/" + os.path.basename(f))
        for f in SITE_DATA: st.put("lists", st.src("site", f), "data/" + os.path.basename(f))
        for f in sorted(os.listdir(st.src("site", "lists"))):
            if f.endswith((".csv", ".md")): st.put("lists", st.src("site", "lists/" + f), "csv/" + f)
        method = os.path.expanduser(cfg.get("lists_method", ""))
        method_row = ""
        if method and os.path.exists(method):
            st.put("lists", method, "METHOD.md"); method_row = "| `METHOD.md` | How the Lists are made, step by step |\n"
        st.write("lists", "README.md", README_LISTS.format(date=date, site_state=git_state(st.src("site")),
                                                           method_row=method_row))

        for f in CHECKER_RECORDS:
            if os.path.exists(st.src("checker", f)):
                st.put("checker", st.src("checker", f), "records/" + f, verbatim=True, rel=f)
        for f in CHECKER_READS:
            dest = "reads/" + f.replace("batches/b6/", "").replace("/", "_")
            src = st.src("checker", f)
            quoted = f.endswith((".json", ".jsonl")) and keys_in(json_docs(src), QUOTE_KEYS)
            if quoted: st.put("checker", src, dest, strip=QUOTE_KEYS); st.verbatim.append((src, f, "checker/" + dest))
            else: st.put("checker", src, dest, verbatim=True, rel=f)
        for f in sorted(os.listdir(st.src("checker", "scripts"))):
            if f.endswith(".py") and not SKIP_SCRIPT.search(f):
                st.put("checker", st.src("checker", "scripts/" + f), "scripts/" + f)
        rows = checker_items(st)
        st.write("checker", "README.md", README_CHECKER.format(date=date, changed=changed_section(st.redacted)))

        for f in STORIES_FILES: st.put("stories", st.src("stories", f), f)
        st.write("stories", "README.md", README_STORIES.format(date=date))

        for folder, entries in st.log.items():
            lines = [f"# {folder}/ staged {date}: sha256 of the source file, sha256 of the staged file, staged path",
                     "# The two hashes differ where private folder paths were replaced, a record was redacted or",
                     "# quoted passages were left out (see README.md)."]
            lines += [f"{o}  {s}  {p}" for o, s, p in entries]
            st.write(folder, "SOURCES.sha256", "\n".join(lines) + "\n")
        bad = scan_staged(st)
        if bad:
            print("\n".join("STOP: " + b for b in bad))
            print("nothing changed: lists/, checker/ and stories/ are as they were")
            return 1
        for folder in STAGED:   # clean scan: swap the new folders in
            old = os.path.join(ROOT, folder)
            if os.path.isdir(old): shutil.rmtree(old)   # both folders belong to this script alone; git keeps the old ones
            os.replace(os.path.join(base, folder), old)
        n = {f: len(e) for f, e in st.log.items()}
        print(f"staged lists/ ({n.get('lists', 0)} files), checker/ ({n.get('checker', 0)} files, items.csv "
              f"{len(rows)} rows) and stories/ ({n.get('stories', 0)} files); {len(st.redacted)} files differ from their "
              f"original on purpose (README.md)")
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=os.path.join(ROOT, ".stage_sources.json"))
    ap.add_argument("--scan-repo", action="store_true", help="scan every tracked file; change nothing")
    a = ap.parse_args()
    if a.scan_repo:
        bad = scan_repo()
        print("\n".join("STOP: " + b for b in bad) if bad else "scan: clean")
        sys.exit(1 if bad else 0)
    if not os.path.exists(a.sources):
        sys.exit(f"no sources file at {a.sources}: it maps top10, listfix, corrections, site, checker (and optional "
                 "lists_method) to their folders, plus 'rewrite' prefixes")
    sys.exit(stage(json.load(open(a.sources))))


if __name__ == "__main__":
    main()
