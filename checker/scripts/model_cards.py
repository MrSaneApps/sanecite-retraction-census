#!/usr/bin/env python3
"""Writes MODEL_CARDS_2026-10-22.md from configs.json plus the research notes below, so the settings each card lists
are the settings judge_v3.py sends (same function builds both). The research gate (llm_api_research_gate.rb --card)
refuses a smoke unless every model has a complete section here.

Usage: model_cards.py configs.json OUT.md"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

R = "model-cards/research/"
SCORE_CHAT = ("mean over the samples of p_i, where p_i = P(major) read from the verdict token's top_logprobs when "
              "the model returns them, else 1 if that sample's verdict is major, else 0. Never the top verdict alone.")
SCORE_TYPED = "mean P(major) from the returned per-option probabilities, over 4 calls with the verdict options rotated."

CARDS = {
    "@cf/cloudflare/clef": dict(
        what="Cloudflare's typed-choice decision model: Qwen 3.8 27B with a frozen backbone, a small trained scoring head and "
             "LoRA adapters; one prefill pass scores every option, no text is generated. Jev-compatible API. $0.24/M input, "
             "output free (grant-covered).",
        sources=["https://developers.cloudflare.com/workers-ai/models/clef/", "https://blog.cloudflare.com/clef-decision-models/",
                 "https://huggingface.co/Cloudflare/clef", "https://docs.typesafe.ai/primitives/choice.md",
                 "https://docs.typesafe.ai/model-jaggedness/jev-1.13.md", "https://docs.typesafe.ai/confidence.md"],
        sop="LLM_VENDOR_API_SOP 'Typed-choice reviews' (lines 113-147): Clef by default, own bars per model, never share "
            "bars with Jev; census Clef 92.0% vs Jev 94.7%. Call-shape table: typed models smoke with --kind typed.",
        settings="No temperature, seed, n or logprobs exist. Live schema: question types noul (P yes), choice (per-option "
                 "probabilities), score (ordered rubric); 1-64 questions; long state is cut silently to fit (our state is at "
                 "most 3,962 tokens, no sign of cuts). TypeSafe documents a first-option bias and +-0.05 run-to-run wobble, "
                 "so we rotate the 4 verdict options (4 calls) and average. Use probabilities, not 'confidence' (it depends "
                 "on the option count). Do not use clef-flash (RAGTruth 35.6).",
        benches=[("clients/translations/outputs/clef-bench-20261013", "Bible-citation bench: recognised 66% of true "
                  "citations (Jev 53%), rejected 99% of near verses (Jev 95%), 0 high-confidence wrong (Jev 9)."),
                 ("clients/translations/outputs/referee-bench", "referee task: balanced 70.6%, second of the CF models, 0.6 s."),
                 ("clients/translations/outputs/held-review", "Via Patrum held-review plans route typed checks to Clef."),
                 ("clients/translations/outputs", "jev-correct-20261002 Clef dry runs (40) and pass log."),
                 ("internal notes", "the SOP itself."),
                 ("outputs/sanecite-phase2-full-20261013", "census panel member; alone 92.0% vs Jev 94.7% on the clean "
                  "confirmation set; 7 silent Jev fallbacks noted in methods."),
                 ("outputs/sanecite-phase2-lean-20261019", "lean census rerun panel member."),
                 ("outputs/sanecite-phase2-pilot-20261013", "pilot panel member (receipts)."),
                 ("outputs/sanecite-stage3-pilot-20261021", "b2 run scored by top choice only (the overnight mistake); "
                  "rescored by P(major) AUC 0.92; pre-registered fresh test at P>=0.10 caught 25/26 majors, flags 30-46%.")],
        overnight="Scored by top choice only. Settings themselves matched the docs; option order was fixed.",
        smoke={"model": "clef", "state": {"text": "The sky is blue."}, "questions": {"ok": {"type": "choice",
               "instructions": "Is the text about the sky?", "criteria": {"yes": "It is about the sky.", "no": "It is not."}}}},
    ),
    "typesafe/jev": dict(
        what="TypeSafe's 'System One' typed-choice model, served through Cloudflare AI Gateway. $0.042/M input, output free; "
             "bills the card-paid gateway balance, not the grant (owner approved for this rerun, 22 Oct 9:16 AM).",
        sources=["https://docs.typesafe.ai/api/system-one.md", "https://docs.typesafe.ai/models.md",
                 "https://docs.typesafe.ai/model-jaggedness/jev-1.13.md", "https://docs.typesafe.ai/cookbooks/citation_check.md",
                 "https://typesafe.ai/blog/jev-1-14", "https://llm-aggrefact.github.io/"],
        sop="LLM_VENDOR_API_SOP call-shape table row 'AI Gateway typesafe/jev (typed)': not in the Workers AI catalog, "
            "smoke on account /ai/run with {model, input:{state, questions}}; 'Typed-choice reviews': card-paid, own bars "
            "(Jev accept 0.8, hold 0.9), billing from the GraphQL record.",
        settings="Same schema as Clef. Limits 64k tokens per request, 32k per question. Known weaknesses: first-option bias "
                 "(rotate options), literal reading, accuracy falls with unrelated text, poor 'none of the above'. Gateway "
                 "route cannot pin a version (jev-latest moves between releases); record the model field returned.",
        benches=[("internal notes", "the SOP."),
                 ("outputs/sanecite-phase2-full-20261013", "census panel tie-breaker; alone 94.7% on the confirmation set."),
                 ("outputs/sanecite-phase2-lean-20261019", "lean census panel member."),
                 ("outputs/sanecite-stage3-pilot-20261021", "named in the rerun plan; not run in stage 3 yet."),
                 ("clients/translations/outputs/clef-bench-20261013", "Bible-citation bench: 53% true recognised, 95% "
                  "near verses rejected, 9 high-confidence wrong."),
                 ("LLM-AggreFact (public)", "Jev 1.13: #2 of 14 at 78.7 balanced accuracy (single source).")],
        overnight="Not run overnight.",
        smoke={"model": "typesafe/jev", "state": {"text": "This is a connectivity test."}, "questions": {"ok": {"type": "choice",
               "instructions": "Is the text a connectivity test?", "criteria": {"yes": "the text says it is a test",
                                                                                 "no": "the text is not a test"}}}},
    ),
    "@cf/moonshotai/kimi-k2.6": dict(
        what="Moonshot Kimi K2.6, paid-access on Workers AI (20 requests/min), batch supported.",
        sources=["https://developers.cloudflare.com/workers-ai/models/kimi-k2.6/", "https://huggingface.co/moonshotai/Kimi-K2.6",
                 "https://www.kimi.com/en/blog/kimi-vendor-verifier", "https://artificialanalysis.ai/models/comparisons/kimi-k2-6-vs-kimi-k2-6-non-reasoning"],
        sop="Call-shape: 'Kimi K2.6 ignores enable_thinking=false; its switch is reasoning_effort none' (llm_bakeoff); OCR "
            "section (lines 97-111) uses Kimi; Throughput: paid model, 20/min, batch overflow via the broker.",
        settings="Live schema: reasoning_effort high|none (default high); temperature default 1; logprobs + top_logprobs "
                 "0-20; n 1-128; response_format json_schema. Moonshot: temperature 1.0 / top_p 0.95 with thinking, 0.6 "
                 "without; max_completion_tokens >= 16000 with thinking; Moonshot blames bad third-party scores on wrong "
                 "decoding settings. AA-LCR long-context reading 70% off, 81% on (single source).",
        benches=[("clients/translations/outputs/benches", "open-checker: as a raiser 35% of findings judged real; pairs "
                  "kimi+X kept 30/32 seeded recall."),
                 ("clients/translations/outputs/defect-bench", "seeded-defect reader recall similar to DeepSeek V4 Pro."),
                 ("clients/translations/outputs/review-bench-20261009", "translation review: thinking on caught 16/20 bad "
                  "vs 12/20 off, but false flags 17/20 vs 10/20."),
                 ("internal notes", "OCR bench 99.3% Latin, 99.7-99.9% Greek."),
                 ("outputs/sanecite-findings-2026-10-22", "overnight brief: part of the cheap panel that over-flagged."),
                 ("outputs/sanecite-stage3-pilot-20261021", "b2 bake + 5-voter panel b3-b5, thinking off, top verdict, "
                  "temperature 0.2; 0 bad parses on b2."),
                 ("outputs/sanecite-phase2-full-20261013", "census pilot: dropped as too slow (~2 min a call).")],
        overnight="Thinking off (reasoning_effort none), temperature 0.2 against Moonshot's 0.6/1.0, top verdict only.",
    ),
    "@cf/deepseek-ai/deepseek-v4.1-flash-1017": dict(
        what="DeepSeek V4.1 Flash (2026-10-17 build), paid-access (20/min). About $0.30/M in, $1.20/M out.",
        sources=["https://developers.cloudflare.com/workers-ai/models/deepseek-v4.1-flash-1017/",
                 "https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash", "https://api-docs.deepseek.com/guides/thinking_mode"],
        sop="Call-shape: 'NV DeepSeek V4 Flash: stream true + reasoning_effort none; extra enable_thinking false can hang' "
            "(NVIDIA route; on CF we send reasoning_effort only and no enable_thinking); Throughput: paid, 20/min.",
        settings="Live schema: reasoning_effort max|high|low|none (default high); logprobs; n; json_schema. Maker: "
                 "temperature 1.0, top_p 1.0. Thinking raised V4-Flash GPQA 71->87 in the maker's table. Catalog shows no "
                 "batch badge for the 1017 build.",
        benches=[("outputs/sanecite-stage3-pilot-20261021", "b2 bake + panel b3-b5, thinking off, temperature 0.2."),
                 ("clients/translations/outputs/review-bench-20261009", "NIM deepseek-v4.1-flash thinking on: 0/20 caught, "
                  "19 replies cut off at the token limit (budget, not the model).")],
        overnight="Thinking off; temperature 0.2 against the maker's 1.0; enable_thinking false also sent (SOP warns it "
                  "can hang on NVIDIA).",
    ),
    "@cf/qwen/qwen3.8-27b": dict(
        what="Qwen 3.8 27B, paid-access (20/min), batch supported. Same base as Clef.",
        sources=["https://developers.cloudflare.com/workers-ai/models/qwen3.8-27b/", "https://huggingface.co/Qwen/Qwen3-32B",
                 "https://artificialanalysis.ai/models/comparisons/qwen3-8-27b-non-reasoning-vs-qwen3-8-27b"],
        sop="Call-shape: Qwen3 (older 30B) has no thinking flag, append /no_think; Qwen 3.8's live schema has "
            "chat_template_kwargs.enable_thinking and reasoning_effort low|medium|xhigh, so the flag is used, no suffix.",
        settings="Maker: thinking temperature 1.0 / top_p 0.95 / top_k 20 (top_k not in the CF schema); non-thinking 0.7 / "
                 "0.8 / presence_penalty 1.5; 'DO NOT use greedy decoding'. AA-LCR 69% off, 82% on (single source).",
        benches=[("outputs/sanecite-findings-2026-10-22", "overnight brief panel."),
                 ("outputs/sanecite-stage3-pilot-20261021", "b2 bake + panel, thinking off + /no_think, temperature 0."),
                 ("outputs/sanecite-phase2-full-20261013", "census tie-breaker trial: did not beat the panel majority.")],
        overnight="Temperature 0 (greedy, which Qwen says not to use), thinking off.",
    ),
    "@cf/zai-org/glm-5.2": dict(
        what="Zhipu GLM 5.2, paid-access (20/min), no batch. About $1.40/M in, $4.40/M out (dearest here).",
        sources=["https://developers.cloudflare.com/workers-ai/models/glm-5.2/", "https://huggingface.co/zai-org/GLM-5.2",
                 "https://artificialanalysis.ai/models/comparisons/glm-5-2-vs-glm-5-2-non-reasoning"],
        sop="Call-shape: 'CF Gemma / GLM: chat_template_kwargs.enable_thinking false (schema default true)'; Throughput: "
            "no batch, capped at ~20/min; doctrine-grade section notes GLM was rate-limited when shared.",
        settings="Live schema: reasoning_effort max|high|none (default max; other values map to max). Maker evals at "
                 "temperature 1.0 / top_p 0.95. AA-LCR 42% off, 78% on: the biggest loss from thinking off. Parse check 22 Oct: reasoning_effort none is IGNORED on CF (1,339 tokens, 5,974 characters of reasoning); enable_thinking false turns it off (56 tokens, 0 reasoning).",
        benches=[("clients/translations/outputs/benches", "open-checker: raiser 37% real; best upholder 33%."),
                 ("clients/translations/outputs/review-bench-20261009", "thinking on: 9/20 caught, 6/20 false flags."),
                 ("outputs/sanecite-phase2-full-20261013", "census tie-breaker trial: did not beat the panel majority."),
                 ("outputs/sanecite-phase2-pilot-20261013", "pilot tie-breaker runs."),
                 ("outputs/sanecite-stage3-pilot-20261021", "named in the plan; not in the overnight bake.")],
        overnight="Not run overnight in stage 3.",
    ),
    "@cf/google/gemma-4-26b-a4b-it": dict(
        what="Google Gemma 4 26B A4B, batch supported, cheapest here (~$0.10/M in, $0.30/M out).",
        sources=["https://developers.cloudflare.com/workers-ai/models/gemma-4-26b-a4b-it/",
                 "https://huggingface.co/google/gemma-4-26B-A4B-it", "https://huggingface.co/google/gemma-4-26B-A4B-it/raw/main/generation_config.json"],
        sop="Call-shape: 'CF Gemma: enable_thinking false (schema default true)' was written for translation drafts; for "
            "judging, Google's published scores are thinking-on, so both arms are run.",
        settings="Google: temperature 1.0, top_p 0.95 (top_k 64 not in the CF schema). With thinking off it can still emit "
                 "empty thought tags; the parser takes the JSON object, and json_schema output is requested.",
        benches=[("outputs/sanecite-phase2-full-20261013", "census panel third model; default-length replies cut off and "
                  "were retried; 6 pairs never answered."),
                 ("outputs/sanecite-phase2-lean-20261019", "lean census panel member."),
                 ("outputs/sanecite-stage3-pilot-20261021", "b2 bake + mix runs, thinking off, temperature 0: 58/200 "
                  "quotes not found in the excerpts."),
                 ("clients/translations/outputs/referee-bench", "gemma-4-31b (other SKU): best balanced 74.2%.")],
        overnight="Thinking off, temperature 0 against Google's 1.0.",
    ),
    "@cf/nvidia/nemotron-3-120b-a12b": dict(
        what="NVIDIA Nemotron 3 Super 120B A12B on Workers AI.",
        sources=["https://developers.cloudflare.com/workers-ai/models/nemotron-3-120b-a12b/",
                 "https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", "https://docs.nvidia.com/nemotron/0.1.0/usage-cookbook/Nemotron-3-Super/AdvancedDeploymentGuide/README.html",
                 "https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Super-Technical-Report.pdf"],
        sop="Call-shape: 'NV Nemotron Super: reasoning_effort none, temp 1.0, top_p 0.95, timeout >= 180 s' is the NVIDIA "
            "API path. On CF the schema has no reasoning_effort; the switches are chat_template_kwargs enable_thinking, "
            "low_effort and force_nonempty_content.",
        settings="NVIDIA: temperature 1.0, top_p 0.95 in both modes; reasoning-off was ~3% of fine-tuning data (tech "
                 "report), so off is a weak mode; force_nonempty_content guards empty answers.",
        benches=[("outputs/sanecite-stage3-pilot-20261021", "b2 bake, thinking off, temperature 0.2: 19/200 replies were "
                  "malformed JSON (lenient parse)."),
                 ("clients/translations/outputs/benches", "open-checker nemo120: pairing with gpt-oss dropped recall 30->25."),
                 ("clients/translations/outputs/defect-bench", "REPORT-nemo120 seeded-defect run."),
                 ("clients/translations/outputs/referee-bench", "NIM Super: balanced 59.4%.")],
        overnight="Thinking off (the under-trained mode), temperature 0.2 against NVIDIA's 1.0; 19/200 malformed replies.",
    ),
    "@cf/openai/gpt-oss-120b": dict(
        what="OpenAI gpt-oss 120B, open rate cap (300/min), batch supported. $0.35/M in, $0.75/M out.",
        sources=["https://developers.cloudflare.com/workers-ai/models/gpt-oss-120b/", "https://huggingface.co/openai/gpt-oss-120b",
                 "https://github.com/openai/gpt-oss", "https://blog.cloudflare.com/openai-gpt-oss-on-workers-ai/"],
        sop="Call-shape: 'CF gpt-oss: schema default max_tokens 256, temperature 0.6; do not invent thinking kwargs'. The "
            "live schema documents reasoning.effort low|medium|high (default medium), so that field is used (not invented).",
        settings="OpenAI: temperature 1.0, top_p 1.0; effort low loses 6-13 points on GPQA; no off switch. Schema has no n or "
                 "logprobs, so 3 separate calls give the samples. Smoke checks that high spends more reasoning tokens than "
                 "medium (proof the field is read).",
        benches=[("outputs/sanecite-findings-2026-10-22", "overnight brief panel."),
                 ("outputs/sanecite-phase2-full-20261013", "census tie-breaker trial: did not beat the panel majority."),
                 ("outputs/sanecite-phase2-pilot-20261013", "pilot runs."),
                 ("outputs/sanecite-stage3-pilot-20261021", "b2 bake + panel b3-b5, temperature 0.6, default effort."),
                 ("clients/translations/outputs/benches", "open-checker: weak raiser, best filter (69% upheld real)."),
                 ("clients/translations/outputs/review-bench-20261009", "13/20 caught, 16/20 false flags, 8 cut off.")],
        overnight="Temperature 0.6 (schema default) against OpenAI's 1.0; effort left at default.",
    ),
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast": dict(
        what="Meta Llama 3.3 70B (fp8 fast), no reasoning mode, open cap, batch supported; 24k context on CF.",
        sources=["https://developers.cloudflare.com/workers-ai/models/llama-3.3-70b-instruct-fp8-fast/",
                 "https://huggingface.co/unsloth/Llama-3.3-70B-Instruct/raw/main/generation_config.json", "https://llm-aggrefact.github.io/"],
        sop="Call-shape table has no Llama row; Throughput lists Llama 3.3 70B as batchable. Schema default max_tokens 256.",
        settings="Meta generation config: temperature 0.6, top_p 0.9. response_format json_schema in schema. No n or "
                 "logprobs: 3 calls give the samples. LLM-AggreFact 74.5 (near GPT-4o 75.9).",
        benches=[("outputs/sanecite-findings-2026-10-22", "overnight brief panel."),
                 ("outputs/sanecite-phase2-pilot-20261013", "pilot runs."),
                 ("outputs/sanecite-stage3-pilot-20261021", "b2 bake + panel b3-b5, temperature 0: 55/200 empty quotes.")],
        overnight="Temperature 0, top verdict only.",
    ),
    "@cf/mistralai/mistral-small-3.1-24b-instruct": dict(
        what="Mistral Small 3.1 24B, no reasoning mode, no batch.",
        sources=["https://developers.cloudflare.com/workers-ai/models/mistral-small-3.1-24b-instruct/",
                 "https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503"],
        sop="No Mistral lines in the SOP (gate printed 0); general rules apply: schema first, smoke, no invented settings.",
        settings="Mistral: temperature 0.15 (also the CF schema default) with a system prompt. JSON control on CF is "
                 "guided_json, not response_format. No n or logprobs: 3 calls; at 0.15 the samples will mostly agree.",
        benches=[("outputs/sanecite-stage3-pilot-20261021", "b2 bake, temperature 0: 1/200 unparsed (fenced JSON with "
                  "citation_type 'cannot_tell')."),],
        overnight="Temperature 0 against Mistral's 0.15; no JSON control.",
    ),
}


def request_kwargs(cfg):
    """Body kwargs judge_v3 sends besides messages and the JSON-schema field (same logic as cf_call)."""
    body = {"temperature": cfg["temperature"]}
    body["max_completion_tokens" if cfg.get("use_max_completion_tokens") else "max_tokens"] = cfg["max_tokens"]
    if cfg.get("enable_thinking") is not None:
        body["chat_template_kwargs"] = {"enable_thinking": cfg["enable_thinking"]}
    if cfg.get("reasoning_effort") is not None:
        body["reasoning_effort"] = cfg["reasoning_effort"]
    body.update(cfg.get("extra") or {})
    return body


def main():
    configs = json.load(open(sys.argv[1]))
    by_model = {}
    for key, cfg in configs.items():
        by_model.setdefault(cfg["model"], []).append((key, cfg))
    out = ["# Model cards for the SaneCite stage 3 rerun (22 Oct 2026)", "",
           "Written before any rerun call. Each card: live model page and schema, the SOP lines that apply, every past study "
           "on disk that used the model (the research gate lists them and refuses a card that skips one), the exact settings "
           "per arm, and how a continuous score is read. Settings lines are generated from model-cards/configs.json, the "
           "file judge_v3.py runs from. Web research: " + R + ". Live schemas: model-cards/schemas/.", "",
           "Every chat arm also sends response_format json_schema (Mistral: guided_json) with the citation schema in "
           "judge_v3.SCHEMA, and the v2 prompt (judge_v2.SYSTEM) unchanged from overnight, so only settings differ. "
           "Smokes send the settings lines below with the gate's {\"ok\":true} prompt (no schema, which would forbid "
           "that reply); the schema is proven by the parse check (20 citations per arm, zero bad parses required).", ""]
    for model, arms in by_model.items():
        c = CARDS[model]
        out += [f"## {model}", "", f"- what: {c['what']}", "- sources: " + " ; ".join(c["sources"]),
                f"- sop: {c['sop']}", f"- settings research: {c['settings']}", "- benches:"]
        out += [f"  - {path}: {note}" for path, note in c["benches"]]
        out += [f"- overnight: {c['overnight']}"]
        typed = arms[0][1].get("kind") == "typed"
        if typed:
            out += [f"- arm {arms[0][0]} ({arms[0][1]['arm']}): questions built by judge_v3.call_typed (v2 definitions, "
                    "verdict options rotated 4 ways); the smoke body is the kwargs line.",
                    f"- kwargs: {json.dumps(c['smoke'])}"]
        else:
            for key, cfg in arms:
                extra = f", {cfg['repeats']} calls per citation" if cfg.get("repeats") else ""
                out += [f"- arm {key} ({cfg['arm']}{extra}):", f"- kwargs ({key}): {json.dumps(request_kwargs(cfg))}"]
        out += [f"- score: {SCORE_TYPED if typed else SCORE_CHAT}", ""]
    open(sys.argv[2], "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
