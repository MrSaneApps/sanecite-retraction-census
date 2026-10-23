#!/usr/bin/env python3
"""Check MANIFEST.sha256: every file against its LATEST listed hash; earlier lines are history.

usage: verify_manifest.py [--update LABEL]

MANIFEST.sha256 only grows. Each dated block records the files registered or changed at that time, so an older line
describes an older version of the file and is not expected to match today. This script:
  - checks each listed file that is in the repository against the last hash listed for it (OK or CHANGED);
  - reports the listed names that were never meant to be here (FOR_THE_RECORD: two private helpers and the
    uncompressed data files hashed at registration) as NOT HERE, which is not an error;
  - reports any other listed file that is missing as MISSING (a registered file was deleted or moved);
  - reports tracked files with no entry at all as UNLISTED;
  - exits 1 if any file is CHANGED, MISSING or UNLISTED.
With --update LABEL it first appends one dated block (headed "# <UTC time> <LABEL>") with the current hash of every
tracked file that is CHANGED or UNLISTED, so the next check passes. It never edits or removes earlier lines.

Lines are "<sha256>  <path>", optionally preceded by an ISO time; text after the path in brackets is a comment.
"""
import hashlib, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "MANIFEST.sha256")
LINE = re.compile(r"^(?:\S*T\S*Z\s+)?([0-9a-f]{64})\s+(.+?)\s*(?:\(.*\))?\s*$")
SKIP = re.compile(r"^(MANIFEST\.sha256|\.github/|\.gitignore$)")
# Listed for the record only: hashed at registration but kept outside the repository (the data files are here
# gzipped, as data/<name>.gz). Any other listed file that is missing is an error.
FOR_THE_RECORD = {"jev_review.py", "llm_bakeoff.py", "stage1_papers.jsonl", "stage2_v31.jsonl", "stage3_clef.jsonl",
                  "stage3_gemma.jsonl", "stage3_jev.jsonl"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def norm(p):
    return p[2:] if p.startswith("./") else p


def entries():
    latest, history = {}, {}
    for l in open(MANIFEST):
        if l.startswith("#") or not l.strip(): continue
        m = LINE.match(l.rstrip("\n"))
        if not m: continue
        h, p = m.group(1), norm(m.group(2))
        if p in latest: history.setdefault(p, []).append(latest[p])
        latest[p] = h
    return latest, history


def tracked():
    out = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    return sorted(p for p in out if p and not SKIP.search(p) and os.path.isfile(os.path.join(ROOT, p)))


def check():
    latest, history = entries()
    files = tracked()
    changed = [p for p in files if p in latest and sha(os.path.join(ROOT, p)) != latest[p]]
    unlisted = [p for p in files if p not in latest]
    absent = sorted(p for p in latest if not os.path.isfile(os.path.join(ROOT, p)))
    missing = [p for p in absent if p not in FOR_THE_RECORD]
    record = [p for p in absent if p in FOR_THE_RECORD]
    ok = len([p for p in files if p in latest]) - len(changed)
    return ok, changed, unlisted, missing, record, history


def main():
    if "--update" in sys.argv:
        label = " ".join(sys.argv[sys.argv.index("--update") + 1:]) or "update"
        _, changed, unlisted, _, _, _ = check()
        todo = sorted(set(changed) | set(unlisted))
        if todo:
            stamp = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())
            with open(MANIFEST, "a") as f:
                f.write(f"# {stamp} {label}\n")
                for p in todo: f.write(f"{sha(os.path.join(ROOT, p))}  ./{p}\n")
            print(f"appended {len(todo)} hashes")
    ok, changed, unlisted, missing, record, history = check()
    for p in changed: print("CHANGED   ", p)
    for p in unlisted: print("UNLISTED  ", p)
    for p in missing: print("MISSING   ", p, "(listed, but the file is gone)")
    for p in record: print("NOT HERE  ", p, "(listed for the record; not in this repository)")
    print(f"{ok} files match their latest hash; {sum(map(len, history.values()))} earlier lines are history; "
          f"{len(changed)} changed, {len(unlisted)} unlisted, {len(missing)} missing, {len(record)} not here")
    sys.exit(1 if changed or unlisted or missing else 0)


if __name__ == "__main__":
    main()
