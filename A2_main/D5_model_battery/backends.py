"""
PE6201 · A2 scaffold — THE TWO BACKENDS
====================================================================
A backend answers ONE question: given the conversation so far, what
does the agent do next?

It returns either
    {"tool": "name", "args": {...}, "thought": "..."}      -> call a tool
    {"final": {...}, "thought": "..."}                     -> conclude

EXACTLY ONE FUNCTION IN THIS WHOLE REPOSITORY KNOWS A VENDOR EXISTS.
It is `_live_call` at the bottom. That is the D5 requirement, and it is
what makes swapping models a one-string change.

--------------------------------------------------------------------
WHY THE SCRIPTED BACKEND IS NOT A TOY

It replays a fixed sequence of decisions for a known case. That makes
your whole run deterministic, free, and reproducible by a stranger -
which is what D5(a) is marked on, and what makes D3(b) and D7 cost
nothing.

It is also the honest way to test your CODE. A guardrail either fires
or it does not; a model has no say in that. Scripting the model's
moves is how you test the parts you wrote.
====================================================================
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import config


# =====================================================================
# SCRIPTED
# =====================================================================
# The moves themselves live with the CASES, in D4_eval_set/scripts.py -
# a script is a statement about one case, not about a vendor. This
# module only knows how to replay one.
#
# Imported as a MODULE rather than as a name, so that anything which
# needs to swap the table for an experiment - D2's sequential arm, D7's
# looping deletion - can rebind scripts.SCRIPTS and have this backend
# see the change.
from D4_eval_set import scripts


class ScriptedBackend:
    """Replays scripts.SCRIPTS[case_id]. Deterministic, free, offline."""

    name = "scripted"

    def __init__(self, case_id):
        if case_id not in scripts.SCRIPTS:
            raise SystemExit(
                "\n  No script for case %r.\n"
                "  The scripted backend replays moves you wrote down; it does\n"
                "  not invent them. Two ways forward:\n"
                "    1. add %r to SCRIPTS in D4_eval_set/scripts.py, or\n"
                "    2. set BACKEND = \"live\" in config.py (this costs money).\n"
                "  Scripted cases so far: %s\n"
                % (case_id, case_id, ", ".join(sorted(scripts.SCRIPTS))))
        self.steps = scripts.SCRIPTS[case_id]
        self.i = 0

    def next_move(self, transcript):
        """`transcript` is ignored on purpose - a script does not react.
        That is what makes it reproducible."""
        if self.i >= len(self.steps):
            return {"final": {"decision": "escalate",
                              "reason": "script ended without a conclusion"},
                    "thought": "script exhausted"}
        step = self.steps[self.i]
        self.i += 1
        return step

    # Token counts on the scripted backend are ESTIMATES, so your cost
    # arithmetic has something to chew on. They are not measurements and
    # you must not report them as such - D6 wants MEASURED counts, which
    # means the live battery.
    #
    # Estimate from transcript CONTENT, not just turn count, so D7's
    # fat_observation deletion is visible offline (a fat return is
    # re-sent on every later turn).
    @staticmethod
    def token_estimate(transcript):
        from common import measure
        body = "".join(str(e.get("content", "")) for e in transcript)
        return 1800 + measure.approx_tokens(body), 120


# =====================================================================
# LIVE
# =====================================================================
class LiveBackend:
    """Real model through OpenRouter. Costs money. D5(b) only."""

    name = "live"

    def __init__(self, case_id, tool_descriptors, system_prompt):
        self.case_id = case_id
        self.tools = tool_descriptors
        self.system_prompt = system_prompt
        # Usage from the most recent OpenRouter call. agent.py adds each
        # (prompt, completion) pair into the run totals, so these must be
        # per-call counts, not a running sum.
        self._last_prompt_tokens = 0
        self._last_completion_tokens = 0
        self._last_usage_estimated = False

    def next_move(self, transcript):
        # The harness passes case_id into this backend, but the model only
        # sees `messages`. Descriptors say "the case id you were given" —
        # without this user turn the live model invents an id (seen:
        # CLM-2024-0892) and every trial escalates / duplicate-loops.
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",
             "content": (
                 "Process claim_id %s. "
                 "Call get_claim with exactly this claim_id first. "
                 "Reply with JSON only, using the shapes in the system prompt."
                 % self.case_id
             )},
        ]
        for entry in transcript:
            messages.append({"role": entry["role"], "content": entry["content"]})
        raw, usage = _live_call(messages)
        self._last_prompt_tokens = int(usage.get("prompt_tokens") or 0)
        self._last_completion_tokens = int(usage.get("completion_tokens") or 0)
        self._last_usage_estimated = bool(usage.get("estimated"))
        return _parse_move(raw)

    def token_estimate(self, transcript):
        """Token counts for the last OpenRouter call.

        Prefer measured usage (prompt_tokens / completion_tokens). Some
        providers omit the usage block; then these are approx_tokens
        estimates and `_last_usage_estimated` is True.
        `transcript` is unused when the API counted the real request.
        """
        return self._last_prompt_tokens, self._last_completion_tokens


def _parse_move(text):
    """The model must answer in JSON. Anything else is a run you cannot
    grade, so say so loudly rather than guessing."""
    if text is None or not str(text).strip():
        return {"final": {"decision": "escalate",
                          "reason": "model returned empty content"},
                "thought": "empty model response"}
    text = str(text).strip()
    # Models often wrap JSON in ```json ... ``` despite instructions.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    move = _loads_move_json(text)
    if move is None:
        return {"final": {"decision": "escalate",
                          "reason": "model did not return parseable JSON"},
                "thought": "unparseable: %s" % text[:200]}
    if isinstance(move, list) and len(move) == 1 and isinstance(move[0], dict):
        # MiniMax occasionally wraps the move in a one-element array.
        move = move[0]
    if not isinstance(move, dict):
        return {"final": {"decision": "escalate",
                          "reason": "model JSON was not an object"},
                "thought": "unparseable: %s" % text[:200]}
    # Prompt shows calls as [["name", {...}]]; agent expects (name, args).
    # Live models often parrot schema placeholders ("string") — drop them.
    from D2_tool_layer import tools as _tools
    if isinstance(move.get("calls"), list):
        move["calls"] = _tools.normalise_tool_calls(move["calls"])

    if "final" in move:
        return move
    if move.get("calls"):
        return move
    if "tool" in move or "name" in move:
        pair = _tools._normalise_one_call({
            "tool": move.get("tool") or move.get("name"),
            "args": move.get("args") or move.get("arguments"),
        })
        if pair is not None:
            move["calls"] = [pair]
            return move
    # Valid JSON but neither a conclusion nor a tool call - common when a
    # model only returns {"thought": "..."}. Escalate loudly; do not KeyError.
    return {"final": {"decision": "escalate",
                      "reason": "model JSON had neither final nor tool calls"},
            "thought": move.get("thought") or ("malformed: %s" % text[:200])}


def _loads_move_json(text):
    """Parse a move object; tolerate prose wrapping a JSON object."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _message_text(message):
    """Pull a usable string out of an OpenRouter/OpenAI message object.

    Some models return content=null (refusal, reasoning-only, or a
    multipart payload). Treat that as empty rather than crashing.
    """
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str) and part.strip():
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text") or part.get("content")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    for key in ("reasoning", "reasoning_content"):
        val = message.get(key)
        if isinstance(val, str) and val.strip():
            # Reasoning text is not the JSON move, but better diagnostics
            # than None; _parse_move will escalate as unparseable.
            return val
    refusal = message.get("refusal")
    if isinstance(refusal, str) and refusal.strip():
        return json.dumps({
            "thought": "model refused",
            "final": {
                "decision": "escalate",
                "reason": "model refusal: %s" % refusal[:300],
            },
        })
    return None


def _live_call(messages):
    """>>> THE ONLY FUNCTION IN THIS REPOSITORY THAT KNOWS A VENDOR <<<

    Everything else speaks in terms of moves and transcripts. Swapping
    vendor means rewriting this one function, and changing MODEL and
    BASE_URL in config.py. Nothing else.

    Returns (content, usage) where usage is the OpenRouter/OpenAI-shaped
    dict with prompt_tokens and completion_tokens. `content` may be an
    empty string when the provider returned null - never None.
    """
    if not config.API_KEY:
        raise SystemExit(
            "\n  BACKEND is 'live' but OPENROUTER_API_KEY is not set.\n"
            "    export OPENROUTER_API_KEY='sk-or-...'\n"
            "  Or set BACKEND = 'scripted' in config.py, which is free.\n")
    body = {
        "model": config.MODEL,
        "messages": messages,
        "temperature": 0,
        # Ask OpenRouter to always include usage when the provider supports it.
        "usage": {"include": True},
    }
    # Ask for JSON when the model supports it. Providers that reject
    # response_format will 400 - fall back without it below.
    body_with_json = dict(body, response_format={"type": "json_object"})
    payload = _openrouter_post(body_with_json)
    if payload is None:
        # Retry without response_format, still asking for usage.
        payload = _openrouter_post(body)
    if payload is None:
        # Last resort: some models reject the usage include flag too.
        bare = {"model": config.MODEL, "messages": messages, "temperature": 0}
        payload = _openrouter_post(bare)
    if payload is None:
        raise SystemExit(
            "\n  OpenRouter call failed for model %r.\n"
            "  Check the model slug in answers_D5.MODELS and your key.\n"
            % config.MODEL)

    choice0 = (payload.get("choices") or [{}])[0]
    message = choice0.get("message") or {}
    content = _message_text(message)
    if content is None:
        # Loud, gradable failure instead of TypeError in json.loads.
        content = json.dumps({
            "thought": "empty provider content",
            "final": {
                "decision": "escalate",
                "reason": "model returned no message content "
                          "(finish_reason=%r)" % choice0.get("finish_reason"),
            },
        })

    usage = _resolve_usage(payload, messages, content)
    return content, usage


def _resolve_usage(payload, messages, content):
    """Build a prompt/completion token pair, never aborting the battery.

    Some providers (seen with MiniMax via OpenRouter) return `usage: {}`
    on the chat response. Prefer, in order:
      1. usage block on the chat payload (incl. alternate key names)
      2. GET /generation?id=... metadata (tokens_prompt / native_*)
      3. local approx_tokens fallback, flagged estimated=True
    """
    usage = _coerce_usage(payload.get("usage"))
    if usage.get("prompt_tokens"):
        return usage

    gen_id = payload.get("id")
    if gen_id:
        fetched = _fetch_generation_usage(gen_id)
        if fetched.get("prompt_tokens"):
            return fetched

    # Fallback: do not kill an 80-trial battery because one provider
    # omitted usage. Label the estimate so D6 can stay honest.
    from common import measure
    prompt_text = json.dumps(messages, ensure_ascii=False, default=str)
    approx_in = max(1, measure.approx_tokens(prompt_text))
    approx_out = max(1, measure.approx_tokens(content or ""))
    if not getattr(_resolve_usage, "_warned", False):
        print()
        print("  WARNING: OpenRouter returned no usage for model %r "
              "(chat usage=%r, generation id=%r)."
              % (config.MODEL, payload.get("usage"), gen_id))
        print("  Falling back to approx_tokens for this run; tag the "
              "battery cost as ESTIMATED in D6 if this persists.")
        print()
        _resolve_usage._warned = True
    return {"prompt_tokens": approx_in,
            "completion_tokens": approx_out,
            "estimated": True}


def _coerce_usage(usage):
    """Normalise OpenRouter / OpenAI / Anthropic-shaped usage dicts."""
    if not isinstance(usage, dict):
        return {}
    prompt = (usage.get("prompt_tokens")
              or usage.get("input_tokens")
              or usage.get("tokens_prompt")
              or usage.get("native_tokens_prompt")
              or 0)
    completion = (usage.get("completion_tokens")
                  or usage.get("output_tokens")
                  or usage.get("tokens_completion")
                  or usage.get("native_tokens_completion")
                  or 0)
    # Reasoning tokens, when billed separately, still count as output.
    reasoning = (usage.get("reasoning_tokens")
                 or usage.get("native_tokens_reasoning")
                 or 0)
    try:
        prompt = int(prompt or 0)
        completion = int(completion or 0) + int(reasoning or 0)
    except (TypeError, ValueError):
        return {}
    if prompt <= 0 and completion <= 0:
        return {}
    out = {"prompt_tokens": prompt, "completion_tokens": completion}
    if usage.get("total_tokens"):
        out["total_tokens"] = usage["total_tokens"]
    return out


def _fetch_generation_usage(gen_id):
    """OpenRouter sometimes fills usage only on GET /generation?id=..."""
    import time
    url = (config.BASE_URL.rstrip("/") + "/generation?id="
           + urllib.parse.quote(str(gen_id), safe=""))
    # Usage can lag a moment behind the chat response.
    for delay in (0.0, 0.4, 1.0):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(
            url,
            headers={"Authorization": "Bearer " + config.API_KEY,
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.load(r)
        except Exception:                                  # noqa: BLE001
            continue
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            continue
        coerced = _coerce_usage({
            "prompt_tokens": data.get("tokens_prompt")
                             or data.get("native_tokens_prompt"),
            "completion_tokens": data.get("tokens_completion")
                                 or data.get("native_tokens_completion"),
            "reasoning_tokens": data.get("native_tokens_reasoning"),
        })
        if coerced.get("prompt_tokens"):
            return coerced
    return {}


def _openrouter_post(body):
    """POST /chat/completions. Returns payload dict, or None on HTTP 400
    that looks like an unsupported optional field (so the caller can
    retry). Other errors still raise."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        config.BASE_URL.rstrip("/") + "/chat/completions",
        data=data,
        headers={"Authorization": "Bearer " + config.API_KEY,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        # Soft-retry triggers: optional request fields this model rejects.
        soft = ("response_format", "usage")
        if exc.code == 400 and any(s in detail.lower() for s in soft):
            return None
        raise SystemExit(
            "\n  OpenRouter HTTP %s for model %r.\n  %s\n"
            % (exc.code, body.get("model"), detail[:800]))


def make_backend(case_id, tool_descriptors=None, system_prompt=""):
    if config.BACKEND == "scripted":
        return ScriptedBackend(case_id)
    if config.BACKEND == "live":
        return LiveBackend(case_id, tool_descriptors or [], system_prompt)
    raise SystemExit("BACKEND must be 'scripted' or 'live', not %r"
                     % config.BACKEND)

