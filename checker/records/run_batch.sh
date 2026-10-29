#!/bin/zsh
# One batch of the SaneCite citation-accuracy check, start to finish, with the method chosen on 22 Oct 2026
# (METHOD_CHOSEN_v2_2026-10-22.md): sample N random citations, judge them with the 5-voter panel, tabulate.
#   run_batch.sh NAME SEED [N=1000]
# Needs a fresh smoked research receipt for the panel models (LLM_VENDOR_API_SOP) in SANE_LLM_API_RECEIPT.
set -u
NAME=${1:?name}; SEED=${2:?seed}; N=${3:-1000}
D="${SANECITE_CHECKER_DIR:-$PWD}"
B="$D/batches/$NAME"
mkdir -p "$B"; cd "$D"
export CF_TOKEN="$CLOUDFLARE_API_TOKEN" CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID:?set your Cloudflare account ID}
echo "$(date +%T) STAGE sample start $NAME seed=$SEED n=$N"
python3 scripts/sample_v2.py "$B/sample.jsonl" "$N" --seed "$SEED" --workers 20 || { echo "$(date +%T) FAIL sample"; exit 1; }
echo "$(date +%T) STAGE judge start"
python3 scripts/judge_v2.py "$B/sample.jsonl" "$B/v2" --prompt v2 --workers 8 \
  --models @cf/deepseek-ai/deepseek-v4.1-flash-1017,@cf/moonshotai/kimi-k2.6 &
python3 scripts/judge_v2.py "$B/sample.jsonl" "$B/v3" --prompt v3 --workers 12 \
  --models @cf/openai/gpt-oss-120b,@cf/meta/llama-3.3-70b-instruct-fp8-fast,@cf/qwen/qwen3.8-27b &
wait
echo "$(date +%T) STAGE tabulate"
python3 scripts/panel_rates.py "$B" > "$B/rates.json" && cat "$B/rates.json"
echo "$(date +%T) EXIT batch $NAME"
