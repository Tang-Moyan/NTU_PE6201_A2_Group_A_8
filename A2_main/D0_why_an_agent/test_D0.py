"""
D0 - TEST SCRIPT
=====================================================================
    python A2_main/D0_why_an_agent/test_D0.py

D0 is mostly a writing deliverable, so most of this script checks that
the answers exist and are internally consistent. Two things it checks
properly, because they are the two places a D0 argument goes wrong:

  1. THE ARITHMETIC. reliability.py is real maths and is unit-tested
     here against Class 4's own worked figures.
  2. THE SECOND ROW OF THE WORKFLOW TEST. If your measured runs all
     take the same number of turns, you have a workflow whatever the
     prose says - and this script will tell you so.

Exit code: 0 complete, 1 answers outstanding, 2 something is wrong.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D0_why_an_agent import answers_D0 as A                    # noqa: E402
from D0_why_an_agent import framework, reliability             # noqa: E402


def test_arithmetic(c):
    """reliability.py against figures we can check by hand."""
    # s = 0.95 over 20 steps is Class 4's opening example: ~35.8%.
    p = reliability.run_success(0.95, 20)
    c.require("run_success(0.95, 20) ~ 0.358", abs(p - 0.3585) < 0.001,
              "got %.4f" % p)

    # The round trip must close: s = P^(1/T) then P = s^T.
    s = reliability.implied_step_reliability(0.80, 6)
    back = reliability.run_success(s, 6)
    c.require("implied_step_reliability round-trips", abs(back - 0.80) < 1e-9,
              "s=%.4f -> P=%.4f" % (s, back))

    # The whole point: same s, fewer turns, higher P.
    short = reliability.run_success(s, 3)
    c.require("cutting turns raises P at constant s", short > 0.80,
              "T=6 -> 80.0%%, T=3 -> %.1f%%" % (short * 100))

    # Bad inputs must raise rather than return something plausible.
    for bad in ((0.0, 5), (1.5, 5), (0.9, 0)):
        try:
            reliability.implied_step_reliability(*bad)
        except ValueError:
            pass
        else:
            c.fail("implied_step_reliability rejects %r" % (bad,))
            return
    c.ok("implied_step_reliability rejects impossible inputs")


def test_weak_step(c):
    """weak_step_candidates on a hand-built results list."""
    results = [
        {"passed": True, "record": {"evidence": ["get_claim", "lookup_policy"]}},
        {"passed": False, "record": {"evidence": ["get_claim", "check_coverage"]}},
        {"passed": False, "record": {"evidence": ["get_claim", "check_coverage"]}},
    ]
    rows = reliability.weak_step_candidates(results)
    top = rows[0][0] if rows else None
    c.require("weak_step_candidates names the tool before the failures",
              top == "check_coverage", "got %r" % top)


def test_answers(c):
    c.templates(A, "D0 answers filled")

    if is_filled(A.RUNG):
        c.require("RUNG is a rung that exists", A.RUNG in range(1, 8),
                  "got %r" % (A.RUNG,))
        if A.RUNG != 7:
            c.todo("RUNG is 7",
                   "you chose %r - defensible only if your steps really do "
                   "not vary; check the measured distribution below"
                   % (A.RUNG,))

    steps_vary = A.WORKFLOW_TEST.get("steps_vary_with_input")
    if is_filled(steps_vary):
        c.require("the deciding row says the steps vary",
                  str(steps_vary).strip().lower().startswith("y"),
                  "you answered %r - that is a workflow, not an agent"
                  % (steps_vary,))

    statements = A.GOOD_RUN_STATEMENTS
    c.require("D0(c) has five statements", len(statements) == 5,
              "got %d" % len(statements))
    if is_filled(statements):
        joined = " ".join(statements).lower()
        c.require("statement 4 covers 'I don't know'",
                  any(k in joined for k in
                      ("don't know", "do not know", "cannot", "not supported",
                       "refuse", "unsupported")),
                  "the statement teams forget, and the one the negative "
                  "cases exist to catch", soft=True)


def test_measured(c):
    """The claims in D0 checked against what the harness recorded."""
    evaluation = store.load("D4_eval")
    turns = store.load("D7_turns")

    if not evaluation:
        c.todo("measured pass rate available",
               "run A2_main/D4_eval_set/eval_runner.py")
    if not turns:
        c.todo("measured median turns available",
               "run A2_main/D7_failures/failure_runs.py")
    if not (evaluation and turns):
        return

    numbers = framework.arithmetic()
    if numbers is None:
        c.fail("the arithmetic could not be computed from the stored numbers")
        return
    s = numbers["implied_step_reliability"]
    cases = evaluation.get("cases") or 0
    c.ok("s = P^(1/T) computed", "P=%.3f  T=%s  s=%.4f"
         % (numbers["measured_pass_rate"], numbers["measured_median_turns"], s))
    if cases < 5:
        c.todo("s is degenerate on %d case(s)" % cases,
               "P=1.0 gives s=1.0, which says nothing. This number only means "
               "something once the D4 set is real - 30 to 50 cases")

    per_case = evaluation.get("per_case") or []
    distinct = {r["turns"] for r in per_case}
    # With only a case or two scripted this CANNOT vary, and that is
    # unfinished work rather than a contradiction. Once the set is real,
    # a single turn count is a genuine finding: it says the second row of
    # the workflow test is 'no', and that you built a workflow.
    c.require("measured turn counts actually vary", len(distinct) > 1,
              "distinct turn counts: %s over %d case(s)%s"
              % (sorted(distinct), cases,
                 " - one value across a real set means the second row of the "
                 "workflow test is 'no', and you have a workflow"
                 if cases >= 5 else " - too few cases scripted to tell yet"),
              soft=(cases < 5), ok_detail="%d distinct: %s"
              % (len(distinct), sorted(distinct)))


def main():
    c = Checker("D0 - why an agent at all")
    test_arithmetic(c)
    test_weak_step(c)
    test_answers(c)
    test_measured(c)
    code = c.finish()
    print()
    print("  Report section 1 preview:  python %s"
          % os.path.join("A2_main", "D0_why_an_agent", "framework.py"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
