"""
D3 - TEST SCRIPT
=====================================================================
    python A2_main/D3_guardrails/test_D3.py

Checks the code layer is actually configured the way the report says
it is, then runs every guardrail case.

THE CHECK WORTH KNOWING ABOUT: answers_D3.LIMITS is compared against
config.py. A report that defends a step cap of 8 while the
committed config says 30 is not a defensible cap, it is a paragraph.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D3_guardrails import answers_D3 as A                      # noqa: E402
from D3_guardrails import checklist                            # noqa: E402


def test_code_layer(c):
    import config
    from D3_guardrails import guardrails

    for name in ("check_turns", "check_budget", "check_duplicate", "gate"):
        c.require("guardrails.%s exists" % name,
                  hasattr(guardrails.Guardrails, name))

    c.require("autonomy is one of the three settings",
              config.AUTONOMY in ("suggest", "confirm", "act"),
              "config.AUTONOMY = %r" % config.AUTONOMY)

    # The report and the committed config must agree.
    for key, intended in A.LIMITS.items():
        if not is_filled(intended):
            continue
        actual = getattr(config, key, None)
        c.require("config.%s matches your defended value" % key,
                  actual == intended,
                  "answers_D3 says %r, config.py says %r - the report would "
                  "be defending a number you do not run" % (intended, actual))

    c.require("every stop is loud", A.LOUD_STOP_CONFIRMED is True,
              "a cap that silently returns an empty answer converts a "
              "visible cost problem into an invisible correctness problem",
              soft=not is_filled(A.LOUD_STOP_CONFIRMED))


def test_checklist(c):
    cases = A.CASES
    c.require("at least 10 guardrail cases", len(cases) >= 10,
              "got %d" % len(cases))

    hostile = checklist.hostile_count()
    c.require("at least 3 hostile free-text cases", hostile >= 3,
              "got %d - both problems carry free text written by someone "
              "outside your organisation" % hostile, soft=True)

    unnamed = [x.get("id") for x in cases if not is_filled(x.get("catches"))]
    c.require("every case names the wrong behaviour it catches", not unnamed,
              "missing on: %s" % ", ".join(str(u) for u in unnamed), soft=True,
              ok_detail="")

    ids = [x.get("id") for x in cases]
    c.require("case ids are unique", len(ids) == len(set(ids)),
              "duplicates: %s" % sorted({i for i in ids if ids.count(i) > 1}),
              ok_detail="")

    results = checklist.run_all()
    held = [r for r in results if r["held"] is True]
    broken = [r for r in results if r["held"] is False]
    unrun = [r for r in results if r["held"] is None]

    c.ok("guardrail cases run", "%d held, %d broken, %d not runnable yet"
         % (len(held), len(broken), len(unrun)))

    for r in broken:
        c.fail("%s did not fire" % r["id"], r["observed"])
    for r in unrun:
        c.todo("%s not runnable yet" % r["id"], r["observed"])


def main():
    c = Checker("D3 - the guardrail layer")
    test_code_layer(c)
    test_checklist(c)
    c.templates(A, "D3 answers filled")
    code = c.finish()
    print()
    print("  Full checklist:  python A2_main/D3_guardrails/checklist.py")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
