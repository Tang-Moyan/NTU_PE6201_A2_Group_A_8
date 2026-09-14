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
# You may also add your own in deletion.py, as long as it is "delete one
# thing" rather than "write a bad agent".

# =====================================================================
# Failure 1 · loop control — required
# =====================================================================
# The agent spins: it repeats actions it has already taken, rereads what
# it already knows, or never reaches a conclusion. Class 4 built exactly
# this — delete one guard from a careful guard chain.
#
# **Watch the result**: after the guard is deleted the run **does not
# crash**. No exception, no error. It repeats a call it has already made,
# burns turns and tokens — **and still returns the correct answer**.
# A pass-rate table will show it as a clean pass.
FAILURE_1 = {
    "case_id": TEMPLATE(
        "Which case do you demonstrate on? Leave None to use the default "
        "scripted case.",
        example="CLM-8842"),
    "fix": TEMPLATE(
        "What is the fix? (For failure 1, that is action de-duplication "
        "itself.)",
        example="Action de-duplication: the guard remembers every "
                "(tool, args) signature this run has already executed and "
                "halts loudly on a repeat."),
    "why_this_layer": TEMPLATE(
        "Why does the fix belong in the code layer?",
        example="A loop has no memory of its own actions unless you give it "
                "one. This IS that memory, and it has to live where the loop "
                "lives."),
    "why_not_code": TEMPLATE(
        "(For failure 1 this cell is 'it is the code layer', but say which "
        "mechanism inside the code layer, and why the other two are not "
        "enough.) "
        "Hint: the step cap **bounds** the damage, it does not **detect** "
        "the fault — and when it stops it does not name the reason. Same "
        "for the budget ceiling.",
        example="Within the code layer, the step cap and the budget ceiling "
                "both failed to fire: neither was breached. They bound the "
                "damage; only de-duplication detects the fault and names it."),
    "why_not_tool": TEMPLATE(
        "Why not fix it at the tool-interface layer?",
        example="No return shape prevents a caller from asking the same "
                "question twice."),
    "why_not_prompt": TEMPLATE(
        "Why not fix it at the prompt layer? "
        "Hint: **the model is the thing that forgot**.",
        example="A prompt fix cannot be relied on - the model is the thing "
                "that forgot. Only the code layer remembers."),
}


# =====================================================================
# Failure 2 · a different layer
# =====================================================================
# Must be tool interface or prompt, not loop control again.
#
# Class 4's worked example is the tool interface: a fat, stale observation
# carrying a landmine — 246 tokens, producing a confident wrong answer,
# **fixed at the interface, not by adding a sentence to the prompt**.
FAILURE_2 = {
    "deletion": TEMPLATE(
        "Choose 'fat_observation' (tool interface) or 'weak_descriptor' "
        "(prompt), or add your own in deletion.py.",
        example="fat_observation"),
    "case_id": TEMPLATE(
        "Which case do you demonstrate on? Leave None to reuse failure 1's "
        "case."),
    "what_goes_wrong": TEMPLATE(
        "After the deletion, what **specifically** happens? It must be "
        "visible to instrumentation.",
        example="check_coverage returns the whole procedures and policies "
                "tables instead of one projection. Observation size per call "
                "goes from ~30 tokens to ~900, and every one of those is "
                "re-sent on every later turn."),
    "how_it_was_detected": TEMPLATE(
        "**Which instrumentation made it visible?** "
        "You cannot report a failure you had no way to notice.",
        example="tokens_in per run, logged while the run happened. The "
                "decision did not change; the bill did."),
    "fix": TEMPLATE("What is the fix?"),
    "why_this_layer": TEMPLATE(
        "Why does the fix belong at this layer? "
        "Hint (Class 4 Section 7): a prompt instruction is paid **on every "
        "call, every run, forever**, and **dies when you change models**; "
        "an interface constraint is **paid once and holds permanently**."),
    "why_not_code": TEMPLATE("Why not fix it at the code layer?"),
    "why_not_prompt": TEMPLATE(
        "Why not fix it at the prompt layer? (If failure 2 itself is at "
        "the prompt layer, change this cell to 'why not at the tool-"
        "interface layer'.)"),
}


# =====================================================================
# Conclusion across both failures
# =====================================================================
CAP_JUSTIFICATION = TEMPLATE(
    "Which measured numbers is your step cap taken from? failure_runs.py "
    "prints median, worst legitimate, and how often the cap was hit. Put "
    "those three numbers in this sentence. "
    "'If your median run is 4 turns and your worst legitimate run is 7, "
    "a step cap of 8 is defensible and a step cap of 30 is decoration.'",
    example="Median 4, worst legitimate 6, so we cap at 8 - two turns of "
            "headroom above anything we have observed working.")

PASS_RATE_DID_NOT_FALL = TEMPLATE(
    "Confirm that putting the guard back did not drop pass rate? "
    "**A cap that stops a runaway run will also truncate a legitimate long "
    "run** — that is trading one failure for another. Check this on **the "
    "whole set**, not one case.",
    example="Pass rate is 100% both with and without the cap across all 40 "
            "cases; no legitimate run comes within two turns of it.")

LOUD_STOP = TEMPLATE(
    "Confirm the stop is loud? "
    "'A cap that silently returns an empty answer is worse than the loop: "
    "it converts a visible cost problem into an invisible correctness "
    "problem.'",
    example=True)
