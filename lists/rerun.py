#!/usr/bin/env python3
"""Re-run the Lists and the charts from this repository and check every file against the published copy.

  python3 lists/rerun.py            # from the repository root; Python 3.9 or later, standard library only

It copies the published site code (code/site/) and the published inputs (data/) into a temporary folder laid out like
the site, runs the code in its public re-run mode (SANECITE_PUBLIC_RERUN=1, with the date pinned to the release day),
and compares each file it writes, byte for byte, with the files the site published: csv/ for the Lists and
charts-csv/ for the charts. It prints one line per file and exits 1 if any differs.

The public re-run mode reads reply dates from data/letters_public.json instead of the site's private letter records,
and skips three checks that guard the live site and change no output: where each reply came from, and whether each
passage and every-citation link lands on a citation the checker lists.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CODE, DATA = os.path.join(HERE, "code", "site"), os.path.join(HERE, "data")
STAGE3 = {"batch6-result.json"}  # read from data/stage3/ by the chart code
ECON = {"econ-result.json"}      # read from data/econ/ by the chart code (economics pilot chart, 9 Nov 2026)
TOP = {"results.json"}           # read from the site root when present


def main() -> int:
    t = tempfile.mkdtemp(prefix="sanecite-rerun-")
    try:
        for d in ("tools/pages", "assets", "data/phase2", "data/stage3", "data/econ", "lists", "charts"):
            os.makedirs(os.path.join(t, d), exist_ok=True)
        for f in ("lists.py", "charts.py", "render_charts.mjs"):
            shutil.copy(os.path.join(CODE, f), os.path.join(t, "tools", f))
        shutil.copy(os.path.join(CODE, "lists.body.html"), os.path.join(t, "tools/pages/lists.body.html"))
        for f in ("site.css", "charts.js"):
            shutil.copy(os.path.join(CODE, f), os.path.join(t, "assets", f))
        for f in os.listdir(DATA):
            src = os.path.join(DATA, f)
            if f in STAGE3:
                dst = os.path.join(t, "data/stage3", f)
            elif f in ECON:
                dst = os.path.join(t, "data/econ", f)
            elif f in TOP:
                dst = os.path.join(t, f)
            else:
                dst = os.path.join(t, "data/phase2", f)
            shutil.copy(src, dst)
        built_on = json.load(open(os.path.join(DATA, "letters_public.json")))["built_on"]
        env = dict(os.environ, SANECITE_PUBLIC_RERUN="1", SANECITE_TODAY=built_on)
        r = subprocess.run([sys.executable, "-B", "-c",
                            "import lists; lists.fill(open('pages/lists.body.html').read())"],
                           cwd=os.path.join(t, "tools"), env=env)
        if r.returncode != 0:
            print("re-run stopped (see the message above)")
            return 1
        bad = n = 0
        for ours, theirs in (("lists", os.path.join(HERE, "csv")), ("charts", os.path.join(HERE, "charts-csv"))):
            for f in sorted(os.listdir(theirs)):
                if not f.endswith((".csv", ".md")) or (ours == "lists" and f == "README.md"):
                    continue
                n += 1
                mine = os.path.join(t, ours, f)
                same = os.path.exists(mine) and open(mine, "rb").read() == open(os.path.join(theirs, f), "rb").read()
                print(("same     " if same else "DIFFERS  ") + f"{ours}/{f}")
                bad += not same
        print(f"{n} files compared, {bad} differ (release day {built_on})")
        return 1 if bad else 0
    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
