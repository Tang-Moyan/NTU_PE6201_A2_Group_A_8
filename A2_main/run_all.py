#!/usr/bin/env python3
"""
A2_main - PRODUCE EVERY NUMBER, IN DEPENDENCY ORDER
=====================================================================
    python A2_main/run_all.py             # everything, scripted, free
    python A2_main/run_all.py --report    # then print the report too

THE ORDER MATTERS AND IT IS NOT ALPHABETICAL. The deliverables read
each other's measurements, so this runs them in the order that makes
each one's inputs exist:

    D2 tool audit      the tool block size (lever 1)
    D2 parallel        sequential vs parallel (lever 2)
    D4 eval            pass rate P, turn distribution      <- D0, D6 need this
    D7 failures        median turns T, the two failures    <- D0, D3 need this
    D2 descriptor      v1 vs v2 return sizes (lever 3)
    D3 checklist       the guardrail cases
    D5 battery         the reproducible scripted run
    D6 levers          the cost model, which reads all of the above
    D0 framework       the arithmetic, which reads D4 and D7

D0 runs LAST even though it is written first, because s = P^(1/T)
needs numbers that only exist once the harness has run. Writing D0's
argument first and measuring it last is the intended order, not an
accident of this script.

Everything here is FREE and OFFLINE. The live battery is the only part
that costs money and it is not run from here - see D5's WORKPLAN.
=====================================================================
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

PIPELINE = [
    ("D2_tool_layer/tool_audit.py", "D2(a) tool block size", "lever 1"),
    ("D2_tool_layer/parallel_ab.py", "D2(c) sequential vs parallel", "lever 2"),
    ("D4_eval_set/eval_runner.py", "D4 evaluation set", "P, and the turn spread"),
    ("D7_failures/failure_runs.py", "D7 failures", "T, and the two deletions"),
    ("D2_tool_layer/descriptor_ab.py", "D2(b) descriptor rewrite", "lever 3"),
    ("D3_guardrails/checklist.py", "D3(b) guardrail checklist", ""),
    ("D5_model_battery/battery.py", "D5(a) reproducible run", ""),
    ("D6_cost_model/levers.py", "D6 cost model", "reads all of the above"),
    ("D0_why_an_agent/framework.py", "D0 the arithmetic", "reads D4 and D7"),
]


def run(script, verbose):
    path = os.path.join(HERE, script)
    proc = subprocess.run([sys.executable, path], capture_output=True)
    if verbose:
        print(proc.stdout.decode("utf-8", "replace"))
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    fmt.h1("A2_main - producing every number, in dependency order")
    print("  Free and offline. The live battery is the only part that costs")
    print("  money, and it is not run from here.")
    print()

    rows = []
    for script, title, why in PIPELINE:
        code, out = run(script, verbose)
        state = "ok" if code == 0 else "exit %d" % code
        rows.append((title, state, why))
        marker = fmt.ok if code == 0 else fmt.fail
        marker("%-34s %s" % (title, why))
        if code != 0 and not verbose:
            tail = [l for l in out.splitlines() if l.strip()][-6:]
            for line in tail:
                print("        %s" % line)

    fmt.h1("Measurements now in A2_main/output/")
    written = store.status()
    if written:
        fmt.table(["record", "written at", "by"], written)
    else:
        fmt.fail("nothing was written - check the failures above")

    print()
    print("  Next:")
    print("      python A2_main/test_all.py          what is still outstanding")
    print("      python A2_main/report/assemble.py   the six sections")

    if "--report" in argv:
        from report import assemble
        assemble.report()
    return 0 if all(r[1] == "ok" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
