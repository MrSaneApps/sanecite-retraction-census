#!/bin/zsh
# Stage 3 pilot: sample 1,600 pairs and judge them as the sample grows. Prints timestamped stage lines for the watcher.
# Needs CF_TOKEN and SANE_LLM_API_RECEIPT in the environment.
set -u
D="${SANECITE_CHECKER_DIR:-$PWD}"
cd "$D"
mkdir "$D/.lock" 2>/dev/null || { echo "$(date +%T) BLOCKED another run holds the lock"; exit 1; }
trap 'rmdir "$D/.lock"; kill $sp 2>/dev/null' EXIT
echo "$(date +%T) STAGE run start"
python3 scripts/sample.py data/sample.jsonl 1600 --workers 10 &
sp=$!
deadline=$((SECONDS + 5 * 3600))
while kill -0 $sp 2>/dev/null && (( SECONDS < deadline )); do
  sleep 300
  python3 scripts/judge.py data/sample.jsonl data/judged --workers 6 || echo "$(date +%T) FAIL judge pass exit $?"
done
wait $sp; echo "$(date +%T) STAGE sampler exit $?"
python3 scripts/judge.py data/sample.jsonl data/judged --workers 6 || echo "$(date +%T) FAIL final judge exit $?"
echo "$(date +%T) EXIT run complete"
