"""
A2_main - IMPORT BOOTSTRAP
=====================================================================
A2_main IS THE SUBMISSION. It carries the agent, the tool layer, the
guardrails, the harness, the backends and the fixture data, and it
runs on its own:

    python A2_main/run_eval.py          <- what a marker runs
    python A2_main/run_all.py           <- every measurement
    python A2_main/test_all.py          <- what is still outstanding

A2_scaffold/ and A2_reference_data/ next door are the pristine
originals. They are useful to diff against when you want to know what
you changed. NOTHING HERE READS THEM AT RUNTIME.

--------------------------------------------------------------------
WHERE THE CODE LIVES, and why it is split this way

Each deliverable owns the code it is marked on, so "what do we still
have to write for D3" has a folder to look in rather than a grep.

    config.py                       the vendor-neutral block      D5
    data/                           fixtures, key, generator      D4
    D1_agent_loop/agent.py          THE LOOP                      D1
    D2_tool_layer/tools.py          the tool implementations      D2
    D2_tool_layer/prompt.py         descriptors -> system prompt  D2
    D3_guardrails/guardrails.py     step cap, budget, dedup, gate D3
    D4_eval_set/harness.py          graders and the judgement queue
    D4_eval_set/scripts.py          the scripted moves, per case
    D5_model_battery/backends.py    scripted and live backends

--------------------------------------------------------------------
Every entry script starts with the same four lines, so it can be run
from any working directory:

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common.bootstrap import init
    init()
=====================================================================
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A2_MAIN = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(A2_MAIN)

DATA = os.path.join(A2_MAIN, "data")
OUTPUT = os.path.join(A2_MAIN, "output")

# The pristine originals. Reference only - see the module docstring.
SCAFFOLD_REFERENCE = os.path.join(REPO_ROOT, "A2_scaffold")
DATA_REFERENCE = os.path.join(REPO_ROOT, "A2_reference_data")

_DONE = False


def _force_utf8_output():
    """Print UTF-8 whatever the console code page says.

    The WORKPLAN files and the TEMPLATE hints are written in Chinese.
    On Windows the default stdout encoding follows the ANSI code page
    (cp936 here), so those bytes come out as mojibake and the one thing
    the test scripts exist to tell you becomes unreadable.
    `errors="replace"` keeps a run alive on a console that genuinely
    cannot render a glyph, rather than dying inside a print.

    Two halves, and both are needed: Python has to WRITE utf-8, and the
    Windows console has to be told to READ it as utf-8. Setting only
    the first swaps one kind of mojibake for another.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def init():
    """Make A2_main importable. Idempotent, so calling it twice is fine."""
    global _DONE
    if _DONE:
        return
    _force_utf8_output()
    if A2_MAIN not in sys.path:
        sys.path.insert(0, A2_MAIN)
    if not os.path.isdir(os.path.join(DATA, "data_A")):
        raise SystemExit(
            "\n  Could not find A2_main/data/data_A/.\n"
            "  Expected it at:\n    %s\n"
            "  This tree carries its own fixtures; it does not read\n"
            "  A2_reference_data/ at runtime.\n" % DATA)
    os.makedirs(OUTPUT, exist_ok=True)
    _DONE = True


def data_file(*parts):
    return os.path.join(DATA, *parts)


def code_file(*parts):
    return os.path.join(A2_MAIN, *parts)


def output_file(*parts):
    os.makedirs(OUTPUT, exist_ok=True)
    return os.path.join(OUTPUT, *parts)
