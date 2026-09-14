"""
D7 - TEST SCRIPT
=====================================================================
    python A2_main/D7_failures/test_D7.py

Checks the SHAPE of the two failures, which is what D7 actually marks:

  - each is a DELETION from the working agent, not a separate bad agent
  - putting X back RECOVERS the behaviour (verified, not asserted)
  - failure 1 is loop control; failure 2 is NOT
  - the caps are justified from the measured distribution
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D7_failures import answers_D7 as A                        # noqa: E402
from D7_failures import deletion, failure_runs                 # noqa: E402


def test_deletions_restore(c):
    """Every deletion must be reversible. This is the D7 shape rule."""
    case = failure_runs._default_case()
    if not case:
        c.fail("no scripted case to test deletions against")
        return None
    for name in deletion.available():
        restored, detail = deletion.verify_restored(case, name)
        c.require("deletion %r reverses cleanly" % name, restored, detail,
                  ok_detail="")
    return case


def test_failure_1(c, case):
    if not case:
        return
    data = failure_runs.before_after("dedup", case, loop_script=True)
    b, a = data["before"], data["after"]

    c.require("failure 1 is in the code layer",
              data["layer"] == "code", "got %r" % data["layer"], ok_detail="")

    c.require("the deletion actually changes the run",
              a["turns"] != b["turns"] or a["tokens"] != b["tokens"],
              "before and after are identical - the deletion did nothing",
              ok_detail="%d -> %d turns, %d -> %d tokens"
                        % (b["turns"], a["turns"], b["tokens"], a["tokens"]))

    c.require("putting X back recovers the behaviour", data["restored"],
              data["restored_detail"], ok_detail="")

    # The lesson: it does not crash, and a pass-rate table would miss it.
    if a["decision"] == b["decision"] and a["stopped_by"] is None:
        c.ok("the broken run returns the RIGHT answer and raises nothing",
             "%.1fx the tokens - visible only because they were counted"
             % (a["tokens"] / max(1, b["tokens"])))
    elif a["stopped_by"]:
        c.ok("a guardrail stopped the broken run",
             "stopped_by=%r - say in the report which guard caught it and "
             "why the other two would not have" % a["stopped_by"])


def test_failure_2(c, case):
    name = A.FAILURE_2.get("deletion")
    if not is_filled(name):
        c.todo("failure 2 not chosen",
               "must be tool interface or prompt: %s"
               % ", ".join(n for n in deletion.available()
                           if deletion.LAYERS[n] != "code"))
        return
    if name not in deletion.available():
        c.fail("unknown deletion %r" % name,
               "available: %s" % ", ".join(deletion.available()))
        return

    layer = deletion.LAYERS.get(name)
    c.require("failure 2 is NOT loop control", layer != "code",
              "%r is in the %s layer - D7 requires the second failure to sit "
              "in the tool interface or the prompt" % (name, layer),
              ok_detail="layer: %s" % layer)

    if layer == "code" or not case:
        return
    data = failure_runs.before_after(name, A.FAILURE_2.get("case_id")
                                     if is_filled(A.FAILURE_2.get("case_id"))
                                     else case)
    b, a = data["before"], data["after"]
    c.require("the deletion actually changes something measurable",
              a["tokens"] != b["tokens"] or a["decision"] != b["decision"],
              "nothing moved - you cannot report a failure you had no way of "
              "noticing",
              ok_detail="%d -> %d tokens, decision %r -> %r"
                        % (b["tokens"], a["tokens"], b["decision"], a["decision"]))
    c.require("putting X back recovers the behaviour", data["restored"],
              data["restored_detail"], ok_detail="")

    c.require("both 'why not' layers are argued",
              is_filled(A.FAILURE_2.get("why_not_code"))
              and is_filled(A.FAILURE_2.get("why_not_prompt")),
              "that judgement is most of the mark", soft=True)


def test_distribution(c):
    dist = failure_runs.turn_distribution()
    if not dist:
        c.fail("no turn distribution", "nothing ran")
        return
    c.ok("turn distribution measured",
         "median %s, worst %s, worst legitimate %s, %d hit the cap"
         % (dist["median_turns"], dist["max_turns"],
            dist["worst_legitimate_turns"], dist["hit_step_cap"]))

    worst = dist["worst_legitimate_turns"] or dist["max_turns"]
    cap = dist["step_cap"]
    c.require("the step cap is close to the evidence", cap <= worst * 3,
              "cap %s against a worst legitimate run of %s - a cap that far "
              "above anything observed is decoration, not a limit"
              % (cap, worst), soft=True)
    c.require("no legitimate run is being truncated", dist["hit_step_cap"] == 0,
              "%d run(s) hit the cap: %s. A cap that stops a runaway also "
              "truncates a legitimate long run - check the pass rate did not "
              "fall" % (dist["hit_step_cap"], dist["capped_cases"]),
              soft=True, ok_detail="")

    c.require("the cap is justified in writing",
              is_filled(A.CAP_JUSTIFICATION),
              "quote the median and the worst legitimate run", soft=True)


def main():
    c = Checker("D7 - two reproduced failures")
    case = test_deletions_restore(c)
    test_failure_1(c, case)
    test_failure_2(c, case)
    test_distribution(c)
    c.templates(A, "D7 answers filled")
    code = c.finish()
    print()
    print("  Full report:  python A2_main/D7_failures/failure_runs.py")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
