#!/usr/bin/env python3
"""Checks before any push of this repository. Install once per clone:

    printf '#!/bin/sh\\nexec python3 scripts/pre_push.py "$@"\\n' > .git/hooks/pre-push && chmod +x .git/hooks/pre-push

git runs it with the refs being pushed on standard input. It refuses the push when
  - a pushed commit holds lists/ or checker/ before LISTS_DAY (the Lists name people; they are published only after
    the reply deadline, SOP H), or
  - verify_manifest.py or the repository scan (stage_release.py --scan-repo) fails.
"""
import datetime, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTS_DAY = datetime.date(2026, 10, 29)   # launch day; change only with the launch date
ZERO = "0" * 40


def today_et():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/New_York")).date()
    except Exception:
        return (datetime.datetime.utcnow() - datetime.timedelta(hours=5)).date()


def has_lists(sha):
    out = subprocess.run(["git", "-C", ROOT, "ls-tree", "--name-only", sha, "lists", "checker"],
                         capture_output=True, text=True).stdout.split()
    return out


def main():
    bad = []
    for line in sys.stdin:
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO: continue
        found = has_lists(parts[1])
        if found and today_et() < LISTS_DAY:
            bad.append(f"{parts[0]} holds {', '.join(found)}: the Lists are published on {LISTS_DAY} (SOP H), not before")
    for cmd in (["scripts/verify_manifest.py"], ["scripts/stage_release.py", "--scan-repo"]):
        r = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            bad.append(f"{' '.join(cmd)} failed:\n" + "\n".join(l for l in r.stdout.splitlines() if not l.startswith("NOT HERE")))
    if bad:
        print("push refused:\n" + "\n".join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
