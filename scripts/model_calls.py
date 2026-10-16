#!/usr/bin/env python3
"""Model calls used by classify.py: Cloudflare Workers AI chat models, and the typed 'choice' lane for
typesafe/jev and @cf/cloudflare/clef.

This is the public copy of the two private helpers named in MANIFEST.sha256 (llm_bakeoff.py, jev_review.py), cut
down to what the census used. The request bodies, model settings and answer parsing are the ones the census ran with.
Left out: a local rate limiter and batch queue (they change when a call is sent, not what is sent or answered) and
code for other projects. Without the rate limiter, run stage3_census.py with few workers; it retries failed calls.

Environment: CF_TOKEN or CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID; optional TYPESAFE_API_KEY (direct Jev route,
used only when the Cloudflare route fails)."""
import json, os, sys, time, urllib.error, urllib.request

DEFAULT_ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
TYPESAFE_API = "https://api.typesafe.ai/v1/systemone"
TRUNCATED_REASONING = "truncated: reasoning only (thinking used the token budget; no answer)"
TRUNCATED_LENGTH = "truncated: length"


def cf_profile(model):
    """Per-model settings. The census panel used gemma-4-26b-a4b-it (this branch) plus the typed lane below."""
    m = model.lower()
    if "glm" in m or "gemma" in m:
        # enable_thinking defaults to true on these models; the census turned it off.
        return {"enable_thinking": False, "temperature": 0.0, "max_tokens": 2500, "use_max_completion_tokens": "gemma" in m}
    return {"temperature": 0.0, "max_tokens": 1800}


def _reasoning_only(result):
    """True when a thinking model ran out of tokens before writing an answer."""
    if not isinstance(result, dict) or result.get("response") or result.get("output_text"):
        return False
    if result.get("choices"):
        msg0 = (result["choices"][0] or {}).get("message") or {}
        return not msg0.get("content") and bool(msg0.get("reasoning_content") or msg0.get("reasoning"))
    if isinstance(result.get("output"), list):
        items = [i for i in result["output"] if isinstance(i, dict)]
        has_reason = any(i.get("type") == "reasoning" for i in items)
        has_answer = any(isinstance(b, dict) and b.get("text") for i in items if i.get("type") != "reasoning"
                         for b in i.get("content") or [])
        return has_reason and not has_answer
    return False


def _cut_off(result):
    if not isinstance(result, dict):
        return False
    choice = (result.get("choices") or [{}])[0] or {}
    return "length" in (choice.get("finish_reason"), result.get("finish_reason"))


def _pick_content(result):
    """Answer text from any Workers AI reply shape; reasoning text is never returned as the answer."""
    if not isinstance(result, dict):
        return None
    content = result.get("response")
    if content is None and result.get("choices"):
        content = (result["choices"][0].get("message") or {}).get("content") or None
    if content is None and result.get("output_text"):
        content = result.get("output_text")
    if content is None and isinstance(result.get("output"), list):
        parts = [b["text"] for item in result["output"] if isinstance(item, dict) and item.get("type") != "reasoning"
                 for b in item.get("content") or [] if isinstance(b, dict) and b.get("text")]
        content = "\n".join(parts) if parts else None
    if content is None:
        return None
    return content if isinstance(content, str) else json.dumps(content)


def cf_call(model, messages, token, account, max_tokens=1800, *, temperature=0.0, enable_thinking=None,
            use_max_completion_tokens=False, timeout=120):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    payload = {"messages": messages, "temperature": temperature}
    payload["max_completion_tokens" if use_max_completion_tokens else "max_tokens"] = max_tokens
    if enable_thinking is not None:
        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}
    body, last_err = json.dumps(payload).encode(), None
    for attempt in range(3):
        t0 = time.time()
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            ms = int((time.time() - t0) * 1000)
            if not data.get("success"):
                return {"error": json.dumps(data.get("errors") or data)[:240], "ms": ms}
            result = data.get("result") or {}
            content = _pick_content(result)
            if content is None:
                if _reasoning_only(result):
                    return {"error": TRUNCATED_REASONING, "ms": ms}
                return {"error": f"empty result: {json.dumps(result)[:200]}", "ms": ms}
            usage = result.get("usage") or {}
            if _cut_off(result):
                return {"error": TRUNCATED_LENGTH, "content": content, "ms": ms, "ct": usage.get("completion_tokens") or 0}
            return {"content": content, "ms": ms, "pt": usage.get("prompt_tokens") or 0,
                    "ct": usage.get("completion_tokens") or 0, "neurons": usage.get("neurons") or 0}
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limited: the caller backs off and retries
                return {"error": f"HTTP 429 rate limited: {e.read().decode(errors='replace')[:200]}",
                        "ms": int((time.time() - t0) * 1000)}
            last_err = e
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(1.0 * (attempt + 1))
    return {"error": f"fetch failed: {last_err}", "ms": 0}


def vendor_call(model, messages, *, cf_token="", account=DEFAULT_ACCOUNT, max_tokens=None):
    if not cf_token:
        return {"error": "no CF_TOKEN", "ms": 0}
    if not account:
        return {"error": "no CLOUDFLARE_ACCOUNT_ID", "ms": 0}
    prof = cf_profile(model)
    return cf_call(model, messages, cf_token, account, max_tokens=int(max_tokens or prof["max_tokens"]),
                   temperature=float(prof.get("temperature", 0.0)), enable_thinking=prof.get("enable_thinking"),
                   use_max_completion_tokens=bool(prof.get("use_max_completion_tokens")))


# ---- typed 'choice' lane (typesafe/jev, @cf/cloudflare/clef)
def _post(url, payload, token, timeout=25):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _cf_jev(state, questions, model):
    token = os.environ.get("CF_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    if not token or not account:
        raise RuntimeError("Cloudflare credentials missing")
    body = _post(f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run",
                 {"model": model, "input": {"state": state, "questions": questions}}, token)
    for _ in range(3):  # Workers AI wraps the reply once, an AI Gateway twice: unwrap until answers show
        if isinstance(body, dict) and "answers" not in body and isinstance(body.get("result"), dict):
            body = body["result"]
        else:
            break
    if not isinstance(body, dict) or "answers" not in body:
        raise RuntimeError("bad reply shape: %s" % str(body)[:160])
    return body


_fallback_noted = False


def jev(state, questions, model="typesafe/jev"):
    """Cloudflare route first; TypeSafe's own API only as a fallback when TYPESAFE_API_KEY is set."""
    global _fallback_noted
    try:
        return _cf_jev(state, questions, model)
    except Exception as e:  # noqa: BLE001
        cf_err = e
    key = os.environ.get("TYPESAFE_API_KEY", "")
    if not key:
        raise SystemExit("Cloudflare route failed (%s); TYPESAFE_API_KEY not set" % cf_err)
    if not _fallback_noted:
        print("JEV-DIRECT-FALLBACK: %s" % cf_err, file=sys.stderr)
        _fallback_noted = True
    return _post(TYPESAFE_API, {"model": "jev-latest", "state": state, "questions": questions}, key)
