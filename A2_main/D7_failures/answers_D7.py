"""
D7 - USER WORK FILE  ("Two reproduced failures")
=====================================================================
Two different failure modes, each fixed at the layer where the fix
belongs.

  "Each must be built as a DELETION FROM YOUR WORKING AGENT, not as a
   separately written bad agent: 'the working agent, minus X.'
   Putting X back must recover the behaviour."

  Failure 1  must be loop-control (code layer)
  Failure 2  you choose, but it MUST be at the tool-interface or prompt
             layer, not loop control again

**"For both failures, state which layer the fix belongs in and why the
other two were the wrong place. That judgement is most of the mark."**

Self-check:  python A2_main/D7_failures/test_D7.py
Full report: python A2_main/D7_failures/failure_runs.py
=====================================================================
"""
from common.template import TEMPLATE

# Available deletions (already implemented in deletion.py; all are
# context managers and restore automatically):
#   code layer       dedup · step_cap · budget_ceiling
#   tool interface   fat_observation
#   prompt           weak_descriptor

# =====================================================================
# Failure 1 · loop control — required
# Measured on CLM-8842 by failure_runs.py: 4 -> 6 turns,
# 21600 -> 38640 tokens, same correct decision, no exception.
# =====================================================================
FAILURE_1 = {
    "case_id": "CLM-8842",
    "fix": (
        "Action de-duplication: the guard remembers every (tool, args) "
        "signature this run has already executed and halts loudly on a "
        "repeat."
    ),
    "why_this_layer": (
        "A loop has no memory of its own actions unless you give it one. "
        "This IS that memory, and it has to live where the loop lives."
    ),
    "why_not_code": (
        "Within the code layer, the step cap and the budget ceiling both "
        "failed to fire: neither was breached (6 turns < 8, 38640 tokens < "
        "60000). They bound the damage; only de-duplication detects the "
        "fault and names it."
    ),
    "why_not_tool": (
        "No return shape prevents a caller from asking the same question "
        "twice."
    ),
    "why_not_prompt": (
        "A prompt fix cannot be relied on - the model is the thing that "
        "forgot. Only the code layer remembers."
    ),
}


# =====================================================================
# Failure 2 · tool interface (fat_observation)
# =====================================================================
FAILURE_2 = {
    "deletion": "fat_observation",
    "case_id": "CLM-8842",
    "what_goes_wrong": (
        "check_coverage's return is wrapped with the entire procedures "
        "and policies tables (21 rows combined, under the 40-row default "
        "cap) alongside the real result, instead of returning just the "
        "projection the next step needs. check_coverage is called once "
        "per line item, so on a 3-line claim like CLM-8842 this padding "
        "is paid three times in one run."
    ),
    "how_it_was_detected": (
        "tokens_in per run, logged while the run happened. On the whole "
        "81-trial set: pass rate unchanged at 100.0% and median turns "
        "unchanged at 3, but cost rose from $0.07335 to $0.08521 "
        "(~16%). The decision never changed; only the bill did - "
        "invisible to a pass-rate table, visible only because tokens "
        "were counted while the run happened."
    ),
    "fix": (
        "Restore the filtered projection: each tool returns only the "
        "fields the next step needs, never the whole table."
    ),
    "why_this_layer": (
        "The fault is the shape of what the tool hands back. A prompt "
        "instruction is paid on every call, every run, forever, and dies "
        "when you change models; an interface constraint is paid once and "
        "holds permanently."
    ),
    "why_not_code": (
        "MAX_TURNS is 8 and MAX_TOKENS_PER_RUN is 60000; the broken run "
        "used only 4 turns and 18,691 tokens - nowhere near either cap. "
        "A step or token cap would only truncate damage after a fat "
        "observation had already been billed and re-sent; here it "
        "would never even fire, let alone stop the tool from returning "
        "the wrong shape."
    ),
    "why_not_prompt": (
        "This failure is a return-shape problem, not a descriptor "
        "problem - unlike the D2(b) descriptor experiment, the tool's "
        "instructions are unchanged here, only what it hands back. "
        "Telling the model to ignore extra fields still ships those "
        "fields in every later turn. The cheaper fix is not to return "
        "them."
    ),
}

# =====================================================================
# Conclusion across both failures
# Numbers from failure_runs.py on the full scripted set (81 trials).
# =====================================================================
CAP_JUSTIFICATION = (
    "Median 3 turns, worst legitimate 4, 0 runs hit the cap, so we cap at "
    "8 - four turns of headroom above anything we have observed working, "
    "tight enough that a runaway still stops inside one extra observation "
    "cycle rather than decorating the config with 30."
)

PASS_RATE_DID_NOT_FALL = (
    "Pass rate is 100% both with and without the de-duplication guard "
    "across all 81 trials on 45 cases; no legitimate run comes within two "
    "turns of the step cap of 8."
)

LOUD_STOP = True
