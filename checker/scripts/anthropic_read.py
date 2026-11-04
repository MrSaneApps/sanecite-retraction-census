#!/usr/bin/env python3
"""Reader on the Anthropic API credit through the Message Batches API (TUNING_CURSOR_ANTHROPIC_2026-10-30.md):
same v2 rules and user message as judge_v2.py (or the v3 checklist with --prompt v3), one request per citation,
JSON through output_config.format. Writes judge_v2's format to batches/<b>/anthropic/<model>[-v3].jsonl so
eval_ref.py and tune_score.py read it.

usage (~/.local/share/anthropic-venv/bin/python, ANTHROPIC_API_KEY loaded):
  anthropic_read.py submit <model> <effort> <batches,...> [--prompt v2|v3] [--draws FILE.json]
      [--sample FILE.jsonl] [--items FILE.jsonl --system-file FILE]
  --sample reads every "ok" row of FILE (no reference filter) under the one batch label given (e.g. b7);
  --items sends prebuilt {"draw", "user"} messages (adjudication) with the system prompt from --system-file.
  anthropic_read.py collect <batch_id>
State: logs/anthropic_batches.json. Spend stop per budget label (env ANTHROPIC_BUDGET, default "tuning", $20; env
ANTHROPIC_STOP_USD sets the stop): refuses a submit whose likely cost x3 would pass it."""
import argparse, json, os, sys, time

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(D, "scripts"))
import judge_v2  # noqa: E402
import score_v3  # noqa: E402

STATE = os.path.join(D, "logs", "anthropic_batches.json")
# Model-call rule: an item Claude refused is never sent to Claude again. collect() records every refusal here by
# custom_id (<batch label>_<draw>); submit() skips any listed request.
STOPS = os.path.join(D, "logs", "claude_stops.json")
WORKSPACE = os.environ.get("ANTHROPIC_WORKSPACE_ID", "wrkspc_01N7A47YLjP9QMqoSkWyPMno")
# Batch prices per million tokens (live pricing page, 30 Oct 2026): in, out, 5-min cache write, cache hit.
PRICE = {"claude-haiku-5-5": (0.05, 0.25, 0.0625, 0.005), "claude-sonnet-5-5": (1.0, 5.0, 1.25, 0.05),
         "claude-opus-5-5": (2.0, 10.0, 2.5, 0.10)}
BUDGET = os.environ.get("ANTHROPIC_BUDGET", "tuning")
STOP_USD = float(os.environ.get("ANTHROPIC_STOP_USD", "20"))
MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "6000"))
SCHEMA = {"type": "object",
          "properties": {"quote": {"type": "string"},
                         "citation_type": {"type": "string", "enum": list(judge_v2.TYPES)},
                         "verdict": {"type": "string", "enum": list(judge_v2.VERDICTS)},
                         "reason": {"type": "string"}},
          "required": ["quote", "citation_type", "verdict", "reason"], "additionalProperties": False}


def client():
    return anthropic.Anthropic(default_headers={"anthropic-workspace-id": WORKSPACE})


def rows_for(b):
    if b == "b6":
        ref = {json.loads(l)["draw"] for l in open(os.path.join(D, "batches/b6/gold/gold.jsonl"))}
        fn = os.path.join(D, "batches/b6/sample_test.jsonl")
    else:
        ref = set(score_v3.load_ref(b))
        fn = os.path.join(D, f"batches/{b}/sample.jsonl")
    rows = {}
    for l in open(fn):
        try:
            r = json.loads(l)
        except json.JSONDecodeError:
            continue
        if r.get("status") == "ok" and r["draw"] in ref:
            rows[r["draw"]] = r
    return rows


def cost(model, u):
    p = PRICE[model]
    return ((u.get("input_tokens") or 0) * p[0] + (u.get("output_tokens") or 0) * p[1]
            + (u.get("cache_creation_input_tokens") or 0) * p[2] + (u.get("cache_read_input_tokens") or 0) * p[3]) / 1e6


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def load_stops():
    return json.load(open(STOPS)) if os.path.exists(STOPS) else {}


def sample_rows(fn):
    rows = {}
    for l in open(fn):
        try:
            r = json.loads(l)
        except json.JSONDecodeError:
            continue
        if r.get("status") == "ok":
            rows[r["draw"]] = r
    return rows


def submit(model, effort, batches, prompt, draws=None, sample=None, items=None, system_file=None):
    system = judge_v2.SYSTEM_V3 if prompt == "v3" else judge_v2.SYSTEM
    if system_file:
        system = open(system_file).read()
    reqs, chars, stops, skipped = [], 0, load_stops(), 0
    for b in batches:
        if items:
            msgs = {j["draw"]: j["user"] for j in map(json.loads, open(items))}
        else:
            msgs = {d: judge_v2.user_msg(r) for d, r in (sample_rows(sample) if sample else rows_for(b)).items()}
        for d, user in sorted(msgs.items()):
            if draws is not None and d not in draws:
                continue
            if f"{b}_{d}" in stops:
                skipped += 1
                continue
            chars += len(user)
            reqs.append(Request(custom_id=f"{b}_{d}", params=MessageCreateParamsNonStreaming(
                model=model, max_tokens=MAX_TOKENS,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}})))
    st = load()
    spent = sum(v.get("usd") or v.get("worst_usd", 0) for v in st.values() if v.get("budget", "tuning") == BUDGET)
    worst = cost(model, {"input_tokens": chars / 3 + len(system) / 3 * len(reqs), "output_tokens": MAX_TOKENS * len(reqs)})
    # Worst case assumes every request uses all of max_tokens; real output is about a tenth of that.
    likely = cost(model, {"input_tokens": chars / 3, "cache_read_input_tokens": len(system) / 3 * len(reqs),
                          "output_tokens": 800 * len(reqs)})
    print(time.strftime("%H:%M:%S"), f"STAGE submit {model} effort={effort} prompt={prompt} n={len(reqs)} "
          f"likely_usd={likely:.2f} worst_usd={worst:.2f} spent_or_committed={spent:.2f} skipped_claude_stops={skipped}", flush=True)
    if spent + likely * 3 > STOP_USD:
        sys.exit(f"BLOCKED spend stop ({BUDGET}): committed {spent:.2f} + 3x likely {likely:.2f} > {STOP_USD}")
    bt = client().messages.batches.create(requests=reqs)
    st[bt.id] = {"model": model, "effort": effort, "prompt": prompt if not system_file else os.path.basename(system_file),
                 "batches": batches, "n": len(reqs),
                 "tag": os.environ.get("ANTHROPIC_TAG", ""), "budget": BUDGET,
                 "submitted": time.time(), "worst_usd": round(likely * 3, 3)}
    json.dump(st, open(STATE, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"STAGE submitted {bt.id}", flush=True)


def collect(batch_id, max_hours=8):
    st = load()
    info = st[batch_id]
    c = client()
    deadline = time.time() + max_hours * 3600
    while time.time() < deadline:
        b = c.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        time.sleep(60)
    else:
        sys.exit(f"FAIL deadline {batch_id}")
    model = info["model"]
    tag = model + ("-" + info["effort"] if info["effort"] != "medium" else "") + ("-v3" if info["prompt"] == "v3" else "") + info.get("tag", "")
    files, usd, n_ok, n_err = {}, 0.0, 0, 0
    stops = load_stops()
    for res in c.messages.batches.results(batch_id):
        b, d = res.custom_id.split("_", 1)
        d = int(d)
        if b not in files:
            os.makedirs(os.path.join(D, f"batches/{b}/anthropic"), exist_ok=True)
            files[b] = open(os.path.join(D, f"batches/{b}/anthropic/{tag}.jsonl"), "w")
        x = {"draw": d, "model": tag, "parsed": None, "error": None, "prompt": info["prompt"]}
        if res.result.type != "succeeded":
            x["error"] = res.result.type
        else:
            m = res.result.message
            u = m.usage.model_dump()
            x["usage"] = {k: u.get(k) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
            x["usd"] = cost(model, u)
            usd += x["usd"]
            text = "".join(bl.text for bl in m.content if bl.type == "text")
            p = judge_v2.parse(text) if m.stop_reason != "refusal" else None
            if m.stop_reason == "refusal":
                stops[res.custom_id] = {"model": model, "batch": batch_id, "when": time.strftime("%Y-%m-%d %H:%M")}
            if p and p.get("verdict") in judge_v2.VERDICTS:
                x["parsed"] = p
            else:
                x["error"] = f"{m.stop_reason}: {text[:120]}"
        n_ok += x["parsed"] is not None
        n_err += x["parsed"] is None
        files[b].write(json.dumps(x) + "\n")
    for f in files.values():
        f.close()
    json.dump(stops, open(STOPS, "w"), indent=1)
    info.update({"usd": round(usd, 4), "ok": n_ok, "errors": n_err, "turnaround_min": round((time.time() - info["submitted"]) / 60, 1)})
    json.dump(st, open(STATE, "w"), indent=1)
    print(time.strftime("%H:%M:%S"), f"EXIT collect {tag} ok={n_ok} errors={n_err} usd={usd:.4f}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("args", nargs="*"); ap.add_argument("--prompt", default="v2")
    ap.add_argument("--draws", default=None); ap.add_argument("--sample", default=None)
    ap.add_argument("--items", default=None); ap.add_argument("--system-file", default=None)
    a = ap.parse_args()
    if a.cmd == "submit":
        submit(a.args[0], a.args[1], a.args[2].split(","), a.prompt,
               set(json.load(open(a.draws))) if a.draws else None, a.sample, a.items, a.system_file)
    else:
        collect(a.args[0])
