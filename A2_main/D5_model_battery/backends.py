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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"final": {"decision": "escalate",
                          "reason": "model did not return parseable JSON"},
                "thought": "unparseable: %s" % text[:200]}


def _live_call(messages):
    """>>> THE ONLY FUNCTION IN THIS REPOSITORY THAT KNOWS A VENDOR <<<

    Everything else speaks in terms of moves and transcripts. Swapping
    vendor means rewriting this one function, and changing MODEL and
    BASE_URL in config.py. Nothing else.

    Returns (content, usage) where usage is the OpenRouter/OpenAI-shaped
    dict with prompt_tokens and completion_tokens.
    """
    if not config.API_KEY:
        raise SystemExit(
            "\n  BACKEND is 'live' but OPENROUTER_API_KEY is not set.\n"
            "    export OPENROUTER_API_KEY='sk-or-...'\n"
            "  Or set BACKEND = 'scripted' in config.py, which is free.\n")
    body = json.dumps({
        "model": config.MODEL,
        "messages": messages,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        config.BASE_URL.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + config.API_KEY,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    content = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage") or {}
    if not usage.get("prompt_tokens"):
        raise SystemExit(
            "\n  OpenRouter returned no usage.prompt_tokens.\n"
            "  Live battery / D6 need measured counts; refusing to report "
            "zeros as measured.\n  Full usage block: %r\n" % usage)
    return content, usage


def make_backend(case_id, tool_descriptors=None, system_prompt=""):
    if config.BACKEND == "scripted":
        return ScriptedBackend(case_id)
    if config.BACKEND == "live":
        return LiveBackend(case_id, tool_descriptors or [], system_prompt)
    raise SystemExit("BACKEND must be 'scripted' or 'live', not %r"
                     % config.BACKEND)
