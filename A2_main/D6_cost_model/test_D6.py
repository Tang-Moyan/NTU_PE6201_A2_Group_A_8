"""
D6 - TEST SCRIPT
=====================================================================
    python A2_main/D6_cost_model/test_D6.py

The arithmetic is unit-tested against the brief's OWN worked example,
so a change to cost_model.py that quietly breaks the break-even
formula is caught here rather than in the report.

The brief's worked figures for Problem A:
    cheap run   US$0.005
    mid-tier    US$0.049 per successful task
    mid-tier measured 92%
    a failed claim costs a claims assessor US$7.60
    -> break-even 91.2%
And the reverse: at US$0.76 per failure the same arithmetic gives 86.2%.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D6_cost_model import answers_D6 as A                      # noqa: E402
from D6_cost_model import cost_model, levers                   # noqa: E402


def test_arithmetic(c):
    # failure_cost from labour
    f = cost_model.failure_cost(38.0, 12)
    c.require("failure_cost(38/hr, 12 min) = 7.60", abs(f - 7.60) < 0.001,
              "got %.4f" % f)

    # The brief's worked break-even, following its own chain:
    #   cheap run C = 0.005, mid-tier run 0.049 measured at 92%,
    #   a failed claim costs 7.60  ->  break-even ~91.2%
    E = cost_model.expensive_model_E(0.049, 0.92, 7.60)
    be = cost_model.break_even_success_rate(0.005, E, 7.60)
    c.require("break-even reproduces the brief's ~91.2%",
              abs(be - 0.912) < 0.005,
              "got %.4f from E=%.4f - if this drifts, the formula or the "
              "definition of E has changed" % (be, E))

    # the reverse the brief gives: a cheaper failure -> break-even ~86.2%
    E_cheapfail = cost_model.expensive_model_E(0.049, 0.92, 0.76)
    be_cheapfail = cost_model.break_even_success_rate(0.005, E_cheapfail, 0.76)
    c.require("a cheaper failure reproduces the brief's ~86.2%",
              abs(be_cheapfail - 0.862) < 0.01,
              "got %.4f. The cheaper it is to be wrong, the more the token "
              "price matters" % be_cheapfail)

    # layer 2 is linear in (1 - P)
    a = cost_model.layer2_fallback(0.90, 7.60)
    b = cost_model.layer2_fallback(0.80, 7.60)
    c.require("layer 2 doubles when failures double", abs(b - 2 * a) < 1e-9,
              "P=0.90 -> %.4f, P=0.80 -> %.4f" % (a, b))

    # cost per successful task must exceed cost per attempt
    per_success = cost_model.cost_per_successful_task(0.005, a, 0.90)
    per_attempt = cost_model.cost_per_task(0.005, a)
    c.require("cost per success exceeds cost per attempt",
              per_success > per_attempt,
              "%.5f vs %.5f - at 90%% you pay for 1.11 attempts per success"
              % (per_success, per_attempt))

    # sensitivity spans the requested range
    rows = cost_model.sensitivity(0.005, 7.60, 0.90, spread=0.10)
    lo, hi = rows[0][0], rows[-1][0]
    c.require("sensitivity spans +/- 10 points",
              abs(lo - 0.80) < 1e-9 and abs(hi - 1.0) < 1e-9,
              "got %.2f..%.2f" % (lo, hi))

    for bad in (0.0, 1.5):
        try:
            cost_model.cost_per_successful_task(0.005, a, bad)
        except ValueError:
            continue
        c.fail("cost_per_successful_task rejects success_rate=%r" % bad)
        return
    c.ok("cost_per_successful_task rejects impossible success rates")


def test_inputs(c):
    c.require("prices filled in",
              is_filled(A.PRICE_IN_PER_M) and is_filled(A.PRICE_OUT_PER_M),
              "layer 1 cannot be computed without them", soft=True)
    c.require("prices were verified against a vendor page",
              is_filled(A.PRICES_CHECKED_ON),
              "quoting a price you did not verify is what D6 marks on",
              soft=True)
    c.require("layer 2 priced from labour, not guessed",
              is_filled(A.HOURLY_RATE_USD)
              and is_filled(A.MINUTES_PER_ESCALATION),
              "failure_cost = hourly rate x minutes / 60", soft=True)
    c.require("fixed monthly costs include your own eval runs",
              is_filled(A.FIXED_MONTHLY),
              "layer 3 - and your evaluation runs are part of it", soft=True)
    c.require("three caps stated", is_filled(A.CAPS),
              "step cap, budget ceiling, monthly limit per user", soft=True)


def test_consistency(c):
    """The caps here must match the ones D3 actually runs."""
    import config
    for key, cap in (("step_cap", "MAX_TURNS"),
                     ("budget_ceiling", "MAX_TOKENS_PER_RUN")):
        value = A.CAPS.get(key)
        if not is_filled(value):
            continue
        actual = getattr(config, cap, None)
        c.require("D6's %s matches config.%s" % (key, cap), value == actual,
                  "answers_D6 says %r, config.py runs %r" % (value, actual))


def test_report(c):
    payload = levers.baseline()
    if payload is None:
        c.todo("the cost model cannot be computed yet",
               "run A2_main/D4_eval_set/eval_runner.py, then fill the prices "
               "and the failure-cost inputs")
        return
    c.ok("baseline computed",
         "US$%.5f variable per run at %.1f%% success"
         % (payload["variable"], payload["success_rate"] * 100))
    if payload.get("estimated_tokens"):
        c.todo("token counts are ESTIMATES from the scripted backend",
               "D6 wants measured counts - take them from the D5 live "
               "battery's usage block")


def main():
    c = Checker("D6 - the cost-to-serve model")
    test_arithmetic(c)
    test_inputs(c)
    test_consistency(c)
    test_report(c)
    c.templates(A, "D6 answers filled")
    code = c.finish()
    print()
    print("  Full report:  python A2_main/D6_cost_model/levers.py")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
