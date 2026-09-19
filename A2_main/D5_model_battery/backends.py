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

    def next_move(self, transcript):
        messages = [{"role": "system", "content": self.system_prompt}]
        for entry in transcript:
            messages.append({"role": entry["role"], "content": entry["content"]})
        raw, usage = _live_call(messages)
        self._last_prompt_tokens = int(usage.get("prompt_tokens") or 0)
        self._last_completion_tokens = int(usage.get("completion_tokens") or 0)
        return _parse_move(raw)

    def token_estimate(self, transcript):
        """Measured usage from the last OpenRouter call (not an estimate).

        OpenRouter mirrors OpenAI's usage block:
            prompt_tokens / completion_tokens
        On reasoning models, thinking tokens are already inside
        completion_tokens — that is how you notice them.
        `transcript` is unused; the API counted the real request.
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
    try:
        move = json.loads(text)
    except json.JSONDecodeError:
        return {"final": {"decision": "escalate",
                          "reason": "model did not return parseable JSON"},
                "thought": "unparseable: %s" % text[:200]}
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
    }
    # Ask for JSON when the model supports it. Providers that reject
    # response_format will 400 - fall back without it below.
    body_with_json = dict(body, response_format={"type": "json_object"})
    payload = _openrouter_post(body_with_json)
    if payload is None:
        payload = _openrouter_post(body)
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
    usage = payload.get("usage") or {}
    if not usage.get("prompt_tokens"):
        raise SystemExit(
            "\n  OpenRouter returned no usage.prompt_tokens.\n"
            "  Live battery / D6 need measured counts; refusing to report "
            "zeros as measured.\n  Full usage block: %r\n" % usage)
    return content, usage


def _openrouter_post(body):
    """POST /chat/completions. Returns payload dict, or None on HTTP 400
    that looks like an unsupported response_format (so the caller can
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
        if exc.code == 400 and "response_format" in detail.lower():
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

