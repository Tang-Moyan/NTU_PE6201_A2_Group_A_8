"""
D1 - TEST SCRIPT
=====================================================================
    python A2_main/D1_agent_loop/test_D1.py

Runs the real agent on a real case and checks the eight loop-contract
clauses. This is the script to re-run after every change to
D1_agent_loop/agent.py - it is the difference between "the loop still
works" and "the loop still returns something".

Writes output/D1_contract.json so the report can quote the turn shape.
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
from D1_agent_loop import answers_D1 as A                      # noqa: E402
from D1_agent_loop import loop_contract                        # noqa: E402

CASE = os.environ.get("A2_CASE", "CLM-8842")


def test_contract(c):
    from D4_eval_set import scripts
    if CASE not in scripts.SCRIPTS:
        c.fail("a scripted case to verify against",
               "%r has no script in D4_eval_set/scripts.py. Script one, or set "
               "A2_CASE to a case that is scripted: %s"
               % (CASE, ", ".join(sorted(scripts.SCRIPTS))))
        return None

    results = loop_contract.verify(CASE)
    for r in results:
        c.require(r.clause, r.held, r.detail)

    shape = loop_contract.turn_shape(CASE)
    if shape:
        fmt.h2("Turn shape on %s - which calls shared a turn" % CASE)
        for i, calls in enumerate(shape, 1):
            print("  turn %d  (%d call%s)  %s"
                  % (i, len(calls), "" if len(calls) == 1 else "s",
                     ", ".join(calls)))
        print()
        print("  A dependency chain cannot be shortened by running things at")
        print("  once. Where a turn holds one call, ask whether that is a")
        print("  real dependency or a missed batch - that is D2(c).")

    store.save("D1_contract",
               {"case": CASE,
                "turn_shape": shape,
                "clauses": [{"clause": r.clause, "held": r.held,
                             "detail": r.detail} for r in results]},
               source="D1/test_D1.py")
    return results


def test_answers(c):
    c.templates(A, "D1 answers filled")

    scope = A.SCOPE_CONFIRMATIONS
    if is_filled(scope):
        wrong = [k for k, v in scope.items() if v is not True]
        c.require("every scope boundary confirmed", not wrong,
                  "not confirmed: %s - each of these is a way to spend the "
                  "fortnight on something that earns no marks"
                  % ", ".join(wrong))

    alt = A.ALTERNATIVE_ARCHITECTURE
    if is_filled(alt):
        c.ok("report section 6 has all three parts",
             "what it would have caught / cost / why you stayed")
    else:
        missing = [k for k, v in alt.items() if not is_filled(v)]
        c.todo("report section 6 alternative architecture",
               "still missing: %s" % ", ".join(missing))


def main():
    c = Checker("D1 - the agent loop")
    test_contract(c)
    test_answers(c)
    return c.finish()


if __name__ == "__main__":
    raise SystemExit(main())
