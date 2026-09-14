"""
D0 - FRAMEWORK  (report section 1, assembled from answers + measurements)
=====================================================================
    python A2_main/D0_why_an_agent/framework.py

Reads answers_D0.py for the argument, and output/D4_eval.json plus
output/D7_turns.json for the numbers. Prints report section 1 in the
order the brief asks for it, and saves the arithmetic to
output/D0_arithmetic.json so D6 quotes the same s, P and T.

Nothing here decides anything. It is the join between what the team
argued and what the harness measured, and its whole job is to make a
disagreement between the two visible.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.template import is_filled                          # noqa: E402
from D0_why_an_agent import answers_D0 as A                    # noqa: E402
from D0_why_an_agent import reliability                        # noqa: E402

LADDER = [
    (1, "Single call", "you", "1 call", "one-shot, well-specified task"),
    (2, "Prompt chain", "you", "2-4 calls", "fixed subtasks with a check between"),
    (3, "Routing", "model picks a lane", "1 + 1 calls", "distinct categories"),
    (4, "Parallelisation", "you", "N calls, one wall-clock", "independent checks, or a vote"),
    (5, "Orchestrator-workers", "model, at runtime", "unpredictable", "the split depends on the input"),
    (6, "Evaluator-optimiser", "model", "unknown rounds", "criteria statable; a second pass helps"),
    (7, "Agent", "model", "unbounded until you cap it", "steps cannot be known in advance"),
]

THREE_QUESTION_TEST = [
    ("Retrieval (RAG)", "your code - one fixed query", "no - a single pass", "no - read-only"),
    ("Agentic retrieval", "the model, at runtime", "yes - it re-queries", "no - read-only"),
    ("Agent", "the model, at runtime", "yes", "YES - it writes, sends, books, pays"),
]


# ---------------------------------------------------------------------
# D0(a)
# ---------------------------------------------------------------------
def section_ladder():
    fmt.h1("D0(a) - the rung, and the defence of it")

    fmt.h2("Class 4's ladder, cheapest first")
    fmt.table(["rung", "pattern", "who decides", "cost", "use it when"],
              [(r, name, who, cost, when) for r, name, who, cost, when in LADDER])

    fmt.h2("Where this problem sits")
    fmt.kv("rung", A.RUNG)
    fmt.paragraph(A.RUNG_DEFENCE)

    fmt.h2("What rungs 1 to 6 would and would not have delivered")
    for rung in range(1, 7):
        name = LADDER[rung - 1][1]
        print("  %d · %-22s %s" % (rung, name, A.RUNG_COUNTERFACTUAL.get(rung)))

    fmt.h2("1 · The workflow test")
    fmt.table(["the question", "workflow", "agent", "ours"], [
        ("Who decides the sequence, and when?", "you, in code",
         "the model, in the moment", A.WORKFLOW_TEST["who_decides_sequence"]),
        ("Does the number of steps vary?", "no", "yes",
         A.WORKFLOW_TEST["steps_vary_with_input"]),
        ("Can you test every path?", "yes", "no - test outcomes",
         A.WORKFLOW_TEST["can_you_test_every_path"]),
        ("What does it cost?", "predictable: n calls", "unpredictable until capped",
         A.WORKFLOW_TEST["what_does_it_cost"]),
    ])
    print()
    print("  The second row is the one that decides it.")
    fmt.paragraph(A.STEP_VARIATION_EVIDENCE)
    _measured_turn_variation()

    fmt.h2("2 · The two conditions - take either away and it is something else")
    print("  Steps not known in advance :")
    fmt.paragraph(A.CONDITION_STEPS_UNKNOWN, indent=4)
    print("  Ground truth at every step :")
    fmt.paragraph(A.CONDITION_GROUND_TRUTH_EACH_STEP, indent=4)

    fmt.h2("3 · The three-question test - where the governance cliff is")
    fmt.table(["", "who picks what to retrieve?", "can it loop and re-query?",
               "can it change the world?"], THREE_QUESTION_TEST)
    print()
    fmt.kv("first irreversible action", A.FIRST_IRREVERSIBLE_ACTION)
    fmt.paragraph(A.IRREVERSIBLE_ACTION_WHY)
    fmt.paragraph(A.GOVERNANCE_CLIFF)


def _measured_turn_variation():
    """The claim above, checked against what the harness actually recorded."""
    payload = store.load("D4_eval")
    if not payload or not payload.get("per_case"):
        print()
        print("  (no measured turn distribution yet - run "
              "A2_main/D4_eval_set/eval_runner.py to fill this in)")
        return
    per_case = payload["per_case"]
    turns = sorted(((c["turns"], c["case_id"]) for c in per_case))
    if not turns:
        return
    print()
    print("  MEASURED, from output/D4_eval.json:")
    fmt.kv("shortest run", "%d turns  (%s)" % turns[0])
    fmt.kv("longest run", "%d turns  (%s)" % turns[-1])
    distinct = sorted({t for t, _ in turns})
    fmt.kv("distinct turn counts", distinct)
    if len(distinct) == 1:
        print("  WARNING: every run took the same number of turns. On this")
        print("  evidence you have a workflow, not an agent - and the second")
        print("  row of the workflow test says so. Check your cases vary.")


# ---------------------------------------------------------------------
# D0(b)
# ---------------------------------------------------------------------
def section_when_not_to():
    fmt.h1("D0(b) - when NOT to build an agent")

    fmt.h2("Test 1 · The ground-truth test")
    print("  What will tell this loop it is wrong, and how fast?")
    print()
    fmt.table(["system of record", "answers in", "objective?"],
              [(s["record"], s["answers_in"], s["objective"])
               for s in A.GROUND_TRUTH_SOURCES])
    print()
    fmt.paragraph(A.GROUND_TRUTH_VERDICT)

    fmt.h2("Test 2 · The arithmetic")
    numbers = arithmetic()
    if numbers is None:
        print("  Not measurable yet. This needs two numbers:")
        print("    P - the run pass rate      -> A2_main/D4_eval_set/eval_runner.py")
        print("    T - the median turn count  -> A2_main/D7_failures/failure_runs.py")
        print("  Both write to A2_main/output/. Re-run this once they exist.")
        return
    fmt.kv("measured run pass rate  P", "%.3f" % numbers["measured_pass_rate"])
    fmt.kv("measured median turns   T", numbers["measured_median_turns"])
    fmt.kv("implied per-step  s = P^(1/T)",
           "%.4f" % numbers["implied_step_reliability"])
    print()
    print("  The same step quality at a different turn count:")
    fmt.table(["turns T", "run success P = s^T"],
              [(t, "%.1f%%" % (p * 100))
               for t, p in numbers["turn_sensitivity"]], aligns=[">", ">"])
    if numbers.get("turns_for_90pc"):
        print()
        fmt.kv("turns affordable at 90% run success",
               numbers["turns_for_90pc"])
    print()
    print("  Way 2 - cut the number of steps - is D2(c). The pass rate you")
    print("  move there is exactly what sets layer 2 of the D6 cost model,")
    print("  because layer 2 is (1 - P) x failure_cost. One argument,")
    print("  measured three times.")

    _weak_step()
    fmt.paragraph(A.ARITHMETIC_READING)
    fmt.paragraph(A.ARITHMETIC_LIMITS)


def arithmetic():
    """The D0(b) Test 2 numbers, or None when the inputs are not measured."""
    evaluation = store.load("D4_eval")
    turns = store.load("D7_turns")
    if not evaluation or not turns:
        return None
    pass_rate = evaluation.get("pass_rate")
    median_turns = turns.get("median_turns")
    if not pass_rate or not median_turns:
        return None
    numbers = reliability.summarise(pass_rate, median_turns)
    store.save("D0_arithmetic", numbers, source="D0/framework.py")
    return numbers


def _weak_step():
    payload = store.load("D4_eval")
    rows = (payload or {}).get("weak_step_candidates")
    if not rows:
        return
    fmt.h2("The weak step - failing runs grouped by the tool call before them")
    fmt.table(["tool", "failures", "appearances", "failure share"],
              [(r[0], r[1], r[2], "%.0f%%" % (r[3] * 100)) for r in rows[:6]],
              aligns=["<", ">", ">", ">"])
    print()
    print("  A weak step usually costs you BOTH terms: a poor return makes")
    print("  the agent re-read, retry or wander, so s falls and T rises at")
    print("  the same time. That is why one fix moves both, and why this and")
    print("  the D7 loop failure are the same investigation from two ends.")
    fmt.paragraph(A.WEAK_STEP_READING)


# ---------------------------------------------------------------------
# D0(c)
# ---------------------------------------------------------------------
def section_good_run():
    fmt.h1("D0(c) - what good looks like")
    print("  Committed BEFORE the first agent commit. D4 is downstream of")
    print("  this list: if a statement is not testable, rewrite it.")
    print()
    for i, statement in enumerate(A.GOOD_RUN_STATEMENTS, 1):
        print("  %d · %s" % (i, statement))
        cases = A.GOOD_RUN_TESTABILITY.get(i)
        print("      tested by: %s" % (cases if is_filled(cases) else cases))


def main():
    section_ladder()
    section_when_not_to()
    section_good_run()
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
