#!/usr/bin/env python3
"""Reader on Cursor plan models (owner, 30 Oct 2026: "start with cheapest models first. like cursors own model then
work up"): same v2 rules and user message as judge_v2.py, one headless cursor-agent call per citation (ask mode, an
empty trusted folder, no tools), written in judge_v2's format so eval_ref.py scores it against batches/b6/gold.

Billing: Cursor draws from the shared Grok/Cursor weekly included pool; additional usage is disabled on the account
(checked 30 Oct 2026 on the usage page: composer-2.5 smoke call "Included", $0). Never call Claude models here
(owner rule: Claude has its own plan).

Usage: cursor_read.py SAMPLE.jsonl OUT.jsonl --model composer-2.5 [--draws FILE.json] [--limit N] [--workers 4]
                      [--pack K] [--prompt v2|v3] [--tag SUFFIX]
--pack K sends K citations in one call and asks for a JSON array (Cursor adds about 18,000 tokens of its own text to
every call, so packing is the cost lever; TUNING_CURSOR_ANTHROPIC_2026-10-30.md). --tag is appended to the model
name in the output rows so packed or v3 runs score as separate readers.
Resumable: draws already in OUT are skipped."""
import argparse, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge_v2

AGENT = os.path.expanduser("~/.local/bin/cursor-agent")
CWD = os.path.expanduser("~/.cache/cursor-empty")
V = set(judge_v2.VERDICTS)
T = set(judge_v2.TYPES)
lock = threading.Lock()


PACK_NOTE = ("\n\nYou will judge {k} separate citations, marked ITEM 1 to ITEM {k}. Judge each one on its own, using "
             "only its own text and excerpts. Answer ONLY with a JSON array of {k} objects in item order, each "
             '{{"item": n, "quote": "...", "citation_type": "...", "verdict": "...", "reason": "one sentence"}}, '
             "no other text.")


def system_for(prompt):
    return judge_v2.SYSTEM_V3 if prompt == "v3" else judge_v2.SYSTEM


def call(model, row, prompt="v2"):
    return run(model, system_for(prompt) + "\n\n" + judge_v2.user_msg(row))


def call_pack(model, rows, prompt="v2"):
    body = system_for(prompt) + PACK_NOTE.format(k=len(rows))
    for n, r in enumerate(rows, 1):
        body += f"\n\n=== ITEM {n} ===\n" + judge_v2.user_msg(r)
    return run(model, body)


def parse_pack(text, k):
    """Items 1..k from a JSON array answer; missing or bad items are None."""
    s, e = text.find("["), text.rfind("]")
    out = [None] * k
    try:
        arr = json.loads(text[s:e + 1])
    except (ValueError, TypeError):
        return out
    for i, x in enumerate(arr if isinstance(arr, list) else []):
        if not isinstance(x, dict):
            continue
        n = x.get("item", i + 1)
        if isinstance(n, int) and 1 <= n <= k and x.get("verdict") in V and x.get("citation_type") in T:
            out[n - 1] = {"verdict": x["verdict"], "citation_type": x["citation_type"],
                          "quote": str(x.get("quote", "")), "reason": str(x.get("reason", ""))}
    return out


def run(model, prompt):
    t0 = time.time()
    p = subprocess.run([AGENT, "-p", "--trust", "--mode", "ask", "--model", model, "--output-format", "json", prompt],
                       cwd=CWD, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"exit {p.returncode}: {(p.stderr or p.stdout)[:300]}")
    d = json.loads(p.stdout)
    if d.get("is_error"):
        raise RuntimeError(f"agent error: {str(d)[:300]}")
    return d.get("result", ""), d.get("usage", {}), int((time.time() - t0) * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("out")
    ap.add_argument("--model", required=True); ap.add_argument("--draws", default="")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pack", type=int, default=1); ap.add_argument("--prompt", default="v2", choices=["v2", "v3"])
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    label = a.model + a.tag
    if "claude" in a.model.lower():
        sys.exit("refused: no Claude models through Cursor (owner rule)")
    os.makedirs(CWD, exist_ok=True)
    want = set(json.load(open(a.draws))) if a.draws else None
    rows = {}
    for l in open(a.sample):
        try: r = json.loads(l)
        except json.JSONDecodeError: continue
        if r.get("status") == "ok" and (want is None or r["draw"] in want): rows[r["draw"]] = r
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(l)["draw"] for l in open(a.out) if l.strip()}
    todo = [d for d in sorted(rows) if d not in done]
    if a.limit: todo = todo[:a.limit]
    print(f"{time.strftime('%H:%M:%S')} STAGE cursor start model={label} pack={a.pack} prompt={a.prompt} todo={len(todo)} done={len(done)}", flush=True)
    stats = {"ok": 0, "fail": 0}

    def one(d):
        row, err, parsed, usage, ms = rows[d], None, None, {}, None
        for attempt in range(3):
            try:
                text, usage, ms = call(a.model, row, a.prompt)
                parsed = judge_v2.parse(text)
                if not parsed or parsed.get("verdict") not in V or parsed.get("citation_type") not in T:
                    raise ValueError(f"off-list or unparsed: {text[:200]}")
                err = None
                break
            except Exception as e:  # noqa: BLE001 - logged per draw, the run continues
                err, parsed = str(e)[:300], None
                time.sleep(5 * (attempt + 1))
        rec = {"draw": d, "model": label, "parsed": parsed,
               "quote_found": judge_v2.quote_ok(parsed.get("quote"), row) if parsed else None,
               "error": err, "usage": usage, "ms": ms, "prompt": a.prompt, "pack": 1}
        with lock:
            with open(a.out, "a") as f: f.write(json.dumps(rec) + "\n")
            stats["fail" if err else "ok"] += 1
            n = stats["ok"] + stats["fail"]
            if err: print(f"{time.strftime('%H:%M:%S')} FAIL draw={d} {err[:160]}", flush=True)
            if n % 25 == 0: print(f"{time.strftime('%H:%M:%S')} STAGE progress {n}/{len(todo)} ok={stats['ok']} fail={stats['fail']}", flush=True)

    def chunk(ds):
        got, err, usage, ms = [None] * len(ds), None, {}, None
        for attempt in range(3):
            try:
                text, usage, ms = call_pack(a.model, [rows[d] for d in ds], a.prompt)
                got = parse_pack(text, len(ds))
                if all(g is None for g in got):
                    raise ValueError(f"unparsed array: {text[:200]}")
                err = None
                break
            except Exception as e:  # noqa: BLE001 - logged per chunk, the run continues
                err = str(e)[:300]
                time.sleep(5 * (attempt + 1))
        share = {k: (v or 0) / len(ds) for k, v in (usage or {}).items() if isinstance(v, (int, float))}
        with lock:
            with open(a.out, "a") as f:
                for d, g in zip(ds, got):
                    e = err or (None if g else "item missing from array")
                    f.write(json.dumps({"draw": d, "model": label, "parsed": g,
                                        "quote_found": judge_v2.quote_ok(g.get("quote"), rows[d]) if g else None,
                                        "error": e, "usage": share, "ms": ms, "prompt": a.prompt, "pack": len(ds)}) + "\n")
                    stats["fail" if e else "ok"] += 1
            n = stats["ok"] + stats["fail"]
            if err: print(f"{time.strftime('%H:%M:%S')} FAIL chunk {ds[0]}.. {err[:160]}", flush=True)
            print(f"{time.strftime('%H:%M:%S')} STAGE progress {n}/{len(todo)} ok={stats['ok']} fail={stats['fail']}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        if a.pack > 1:
            list(ex.map(chunk, [todo[i:i + a.pack] for i in range(0, len(todo), a.pack)]))
        else:
            list(ex.map(one, todo))
    print(f"{time.strftime('%H:%M:%S')} EXIT cursor model={a.model} ok={stats['ok']} fail={stats['fail']}", flush=True)


if __name__ == "__main__":
    main()
