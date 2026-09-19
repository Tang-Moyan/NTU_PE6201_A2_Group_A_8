"""
D4 - TEST SCRIPT
=====================================================================
    python A2_main/D4_eval_set/test_D4.py

Checks the SET before it checks the agent, because a set that is the
wrong shape produces a number that means nothing however good the
agent is.
=====================================================================
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt                                         # noqa: E402
from common.bootstrap import data_file                         # noqa: E402
from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D4_eval_set import answers_D4 as A                        # noqa: E402
from D4_eval_set import eval_runner, sync_fixtures             # noqa: E402

NEGATIVE = ("escalate", "request_document")


def _key():
    with open(data_file("expected_outcomes_A.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_set_shape(c):
    key = _key()
    total = len(key)
    negatives = [
        row for row in A.EXTRA_LABELS
        if row.get("expected_decision") in NEGATIVE
    ]

    c.require("30-50 cases", 30 <= total <= 50,
              "the answer key has %d. A 10-case set cannot tell two policies "
              "apart" % total, soft=total < 30)
    c.require("6-10 negative cases", 6 <= len(negatives) <= 10,
              "got %d (the floor is 2, but a set this size should carry "
              "6-10)" % len(negatives), soft=len(negatives) < 6)

    # Label hygiene, mirroring check_my_data.py so a broken label is
    # caught here too rather than only at the data checker.
    bad = []
    for row in key:
        cid = row.get("case_id")
        dec = row.get("expected_decision")
        if dec == "escalate" and not row.get("trigger"):
            bad.append("%s: escalation with no single trigger" % cid)
        if dec == "request_document" and not row.get("missing"):
            bad.append("%s: a request with nothing named" % cid)
        if row.get("missing") and str(row["missing"]).strip().lower() in (
                "more information", "more info", "incomplete"):
            bad.append("%s: 'more information' scores nothing - name the "
                       "exact thing" % cid)
    c.require("every label is well formed", not bad, "; ".join(bad))

    families = {r.get("family") for r in key if r.get("family")}
    c.ok("negative-case families represented", "%d distinct" % len(families))


def test_new_cases(c):
    clash = sync_fixtures.collisions()
    c.require("no new case reuses a shipped id", not clash,
              "collisions: %s" % ", ".join(clash), ok_detail="")

    missing, orphan = sync_fixtures.unlabelled()
    c.require("every new claim has a label", not missing,
              "unlabelled: %s" % ", ".join(missing), soft=True, ok_detail="")
    c.require("every new label has a claim", not orphan,
              "orphan labels: %s" % ", ".join(orphan), ok_detail="")

    written = len(A.EXTRA_CLAIMS)
    c.require("about 25 new claims written", written >= 15,
              "%d written; 15 are shipped, D4 wants 30-50 in total"
              % written, soft=True)


def test_policy(c):
    if is_filled(A.TRIALS_NEGATIVE):
        c.require("negatives get several trials", A.TRIALS_NEGATIVE >= 3,
                  "got %r - a single trial cannot tell a real refusal from a "
                  "lucky one" % (A.TRIALS_NEGATIVE,))
    c.require("a judgement grader is named", is_filled(A.JUDGEMENT_GRADER),
              "person or model - and if it is a model, say so in the report",
              soft=True)


def test_run(c):
    results, queue, unscripted = eval_runner.run()
    if not results:
        c.fail("nothing ran", "no case has both a label and a script")
        return
    s = eval_runner.summarise(results)
    c.ok("evaluation ran", "%.1f%% over %d trial(s) on %d case(s)"
         % (s["pass_rate"] * 100, s["trials"], s["cases"]))

    if unscripted:
        c.todo("%d labelled case(s) have no script" % len(unscripted),
               ", ".join(unscripted[:8]) + ("..." if len(unscripted) > 8 else ""))

    c.require("isolation holds", eval_runner.isolation_holds(results[0]["case_id"]),
              "two clean runs of the same case differ - state is leaking "
              "between runs and no case may depend on a previous one",
              ok_detail="two clean runs of the same case are identical")

    distinct = {r["turns"] for r in s["per_case"]}
    c.require("turn counts vary across the set", len(distinct) > 1,
              "every run took the same number of turns: %s. D0's workflow "
              "test needs this to vary" % sorted(distinct), soft=True)


def main():
    c = Checker("D4 - the evaluation set")
    test_set_shape(c)
    test_new_cases(c)
    test_policy(c)
    test_run(c)
    c.templates(A, "D4 answers filled")
    code = c.finish()
    print()
    print("  Add cases:  edit answers_D4.py, then")
    print("    python A2_main/D4_eval_set/sync_fixtures.py --write")
    print("    python A2_main/data/make_fixtures_A.py")
    print("    python A2_main/data/check_my_data.py")
    print("  Measure  :  python A2_main/D4_eval_set/eval_runner.py")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
