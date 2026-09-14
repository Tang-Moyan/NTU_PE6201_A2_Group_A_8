"""
PE6201 · A2 scaffold — CONFIGURATION
====================================================================
THIS IS THE VENDOR-NEUTRAL BLOCK THE BRIEF ASKS FOR (D5).

Everything that knows which model you are using lives here and in
backend_live.py, and nowhere else. Switching model is changing a string.

    BACKEND = "scripted"   free, deterministic, no key, no network.
                           THIS MUST BE THE DEFAULT IN WHAT YOU SUBMIT.
                           A marker clones your repository and runs it
                           this way. If it does not run, D5(a) fails and
                           Technical Execution is capped.

    BACKEND = "live"       real model through OpenRouter. Costs money.
                           Only D5(b) - your model battery - needs this.

The guardrail checklist (D3b), the reproducible run (D5a) and the two
failure reproductions (D7) ALL run scripted. Only the battery is live.
====================================================================
"""
import os

# ─────────────────────────────────────────────────────────────────────
# THE THREE STRINGS. Change these, change nothing else.
# ─────────────────────────────────────────────────────────────────────
BACKEND = "scripted"          # "scripted" | "live"

MODEL = "openai/gpt-4o-mini"  # only used when BACKEND == "live"
BASE_URL = "https://openrouter.ai/api/v1"

# Your key never goes in this file. Put it in the environment:
#     export OPENROUTER_API_KEY="sk-or-..."
# In Colab:  os.environ["OPENROUTER_API_KEY"] = "sk-or-..."
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ─────────────────────────────────────────────────────────────────────
# WHICH PROBLEM. This repository does Problem A - health-insurance claim
# first response. Problem B has been stripped out of the scaffold and the
# reference data, so this string is fixed.
# ─────────────────────────────────────────────────────────────────────
PROBLEM = "A"

# ─────────────────────────────────────────────────────────────────────
# GUARDRAIL LIMITS (D3a). These are the code layer. Set them from
# EVIDENCE, not from a round number - see D7. If your median run is 4
# turns and your worst legitimate run is 7, a cap of 8 is defensible
# and a cap of 30 is decoration.
#
# TODO(D3/limits): set these three from your MEASURED turn distribution.
#   Run A2_main/D7_failures/failure_runs.py first - it prints the median,
#   the worst legitimate run and how many runs hit the cap. Then record
#   the reasoning in D3_guardrails/answers_D3.py::LIMITS_EVIDENCE.
#   test_D3.py compares the two and fails if they disagree, because a cap
#   defended in the report that config.py does not run is a paragraph,
#   not a cap.
# ─────────────────────────────────────────────────────────────────────
MAX_TURNS = 8                 # step cap
MAX_TOKENS_PER_RUN = 60000    # budget ceiling
AUTONOMY = "confirm"          # "suggest" | "confirm" | "act"

# TODO(D6/cap): D6 asks for THREE caps and the scaffold ships two. Add a
#   monthly limit per user, decide what it is measured in (claims per
#   assessor account?) and enforce it somewhere you can point at. Right
#   now this is a number with no code behind it.
MONTHLY_LIMIT_PER_USER = None
#   suggest  - the agent proposes; a human does everything
#   confirm  - the agent does everything EXCEPT the irreversible step,
#              which waits for a yes. THE GATE GOES IN FRONT OF THE
#              IRREVERSIBLE STEP, not in front of the agent.
#   act      - the agent completes the irreversible step itself

# ─────────────────────────────────────────────────────────────────────
# WHERE THE DATA IS. A2_main carries its own copy in data/, so this
# repository runs on its own. A2_reference_data/ next door is the
# pristine original - useful to diff against, never read at runtime.
# Override with the environment variable A2_DATA rather than editing.
# ─────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))

_CANDIDATES = [
    os.environ.get("A2_DATA", ""),
    os.path.join(HERE, "data"),
]


def data_root():
    """Find the folder that holds data_A/.

    Fails LOUDLY with instructions rather than returning something wrong.
    A silent wrong path here is exactly the failure the data guide warns
    about: your tools return nothing and the run still looks fine.
    """
    for c in _CANDIDATES:
        if c and os.path.isdir(os.path.join(c, "data_A")):
            return os.path.abspath(c)
    raise SystemExit(
        "\n  Could not find the fixture data.\n"
        "  I looked for a folder containing data_A/ in:\n"
        + "".join("    %s\n" % os.path.abspath(c) for c in _CANDIDATES if c)
        + "\n  Fix it either way:\n"
        "    1. restore A2_main/data/, or\n"
        "    2. set A2_DATA=/path/to/a/folder/holding/data_A\n")


# ─────────────────────────────────────────────────────────────────────
# PRICES, US dollars per MILLION tokens. Section 7 of the brief.
# Checked against vendor pages 28 August 2026. RE-CHECK THEM: quoting a
# price you did not verify is the kind of thing D6 is marked on.
# ─────────────────────────────────────────────────────────────────────
PRICE_IN = 0.10
PRICE_OUT = 0.40


def _stale_bytecode_warning():
    """Detect Python reusing an out-of-date __pycache__ copy of THIS file.

    WHY THIS EXISTS. Changing AUTONOMY = "confirm" to "suggest" leaves the
    file the SAME SIZE. If the edit lands in the same second as the last
    run, Python's staleness check - (source mtime, source size) - sees no
    change and silently reuses the compiled copy. You edit the file, run
    it, and get the OLD value with no error at all.

    That happened during development of this scaffold, so it will happen
    to you. It is also a small lesson in its own right: the most expensive
    bugs are the ones that produce a confident, wrong, unremarkable answer.

    The fix is `rm -rf __pycache__`, or in a notebook, restart the kernel.
    """
    import re
    try:
        src = open(os.path.join(HERE, "config.py"), encoding="utf-8").read()
    except OSError:
        return ""
    out = []
    for name, live in (("BACKEND", BACKEND), ("AUTONOMY", AUTONOMY)):
        m = re.search(r'^%s\s*=\s*"([^"]*)"' % name, src, re.M)
        if m and m.group(1) != live:
            out.append("%s is %r in config.py but %r in memory"
                       % (name, m.group(1), live))
    if not out:
        return ""
    return ("\n  !! STALE BYTECODE - PYTHON IS IGNORING YOUR EDIT !!\n"
            + "".join("     %s\n" % o for o in out)
            + "     fix:  rm -rf __pycache__      (in a notebook: restart the kernel)\n")


def summary():
    """One line, printed at the top of every run, so you always know
    which backend produced the numbers you are looking at.

    It also carries the stale-bytecode check, because this line is the
    one place every entry point already prints."""
    where = "FREE, deterministic" if BACKEND == "scripted" else "LIVE - this costs money"
    model = "(no model)" if BACKEND == "scripted" else MODEL
    line = ("BACKEND=%s  %s  |  PROBLEM=%s  |  model=%s  |  "
            "cap=%d turns  |  autonomy=%s"
            % (BACKEND, where, PROBLEM, model, MAX_TURNS, AUTONOMY))
    return line + _stale_bytecode_warning()
