#!/usr/bin/env python3
"""
A2_main - RUN EVERY DELIVERABLE'S TEST
=====================================================================
    python A2_main/test_all.py            # all eight, one table
    python A2_main/test_all.py D2 D4      # just those

Runs each test_Dx.py as a SEPARATE PROCESS, so one deliverable's
module-level state cannot leak into another's and one crash cannot
take the rest down. That is the same isolation rule D4 imposes on
evaluation cases, applied to the deliverables themselves.

Exit codes, per deliverable and overall:

    0   complete and verified
    1   nothing broken, work outstanding
    2   something is WRONG, not merely unwritten

Read the 2s first. A FAIL means the framework caught a contradiction -
a cap defended in the report that config.py does not run, a dependency
rule the scripts break, a deletion that does not reverse.
=====================================================================
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.bootstrap import init
init()

from common import codemap, fmt                                # noqa: E402
from common.bootstrap import A2_MAIN                           # noqa: E402

DELIVERABLES = [
    ("D0", "D0_why_an_agent", "why an agent at all"),
    ("D1", "D1_agent_loop", "the agent loop"),
    ("D2", "D2_tool_layer", "the tool layer"),
    ("D3", "D3_guardrails", "the guardrail layer"),
    ("D4", "D4_eval_set", "the evaluation set"),
    ("D5", "D5_model_battery", "the model battery"),
    ("D6", "D6_cost_model", "the cost model"),
    ("D7", "D7_failures", "two reproduced failures"),
]

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = {0: "complete", 1: "work to do", 2: "SOMETHING IS WRONG"}


def run_one(folder, verbose):
    script = os.path.join(HERE, folder, "test_%s" % folder.split("_")[0] + ".py")
    if not os.path.exists(script):
        return None, "no test script at %s" % script
    proc = subprocess.run([sys.executable, script], capture_output=True)
    out = proc.stdout.decode("utf-8", "replace")
    if verbose:
        print(out)
    summary = _summary_line(out)
    return proc.returncode, summary


def _summary_line(out):
    for line in out.splitlines():
        if " ok, " in line and " to do, " in line:
            return line.strip()
    return "(no summary)"


def main(argv):
    wanted = [a.upper() for a in argv[1:] if not a.startswith("-")]
    verbose = "-v" in argv or "--verbose" in argv
    todo = [d for d in DELIVERABLES if not wanted or d[0] in wanted]

    fmt.h1("A2_main - every deliverable")
    print("  Running each test as its own process, so nothing leaks.")

    rows, worst = [], 0
    for code, folder, title in todo:
        if verbose:
            fmt.h2("%s - %s" % (code, title))
        rc, summary = run_one(folder, verbose)
        if rc is None:
            rows.append((code, title, "MISSING", summary))
            worst = 2
            continue
        worst = max(worst, rc)
        rows.append((code, title, STATE.get(rc, "exit %d" % rc), summary))

    fmt.h1("Summary")
    code = codemap.by_deliverable(A2_MAIN)
    fmt.table(["", "deliverable", "state", "code to write", "detail"],
              [(r[0], r[1], r[2], len(code.get(r[0], [])) or "-", r[3])
               for r in rows])
    print()
    print("  'code to write' counts TODO(Dn/...) markers in the")
    print("  implementation. The 'detail' column counts TEMPLATE slots in")
    print("  the answers files. Two different kinds of outstanding work:")
    print("      python A2_main/code_todo.py     what to BUILD")
    print("      python A2_main/test_all.py      what to DECIDE")

    print()
    broken = [r for r in rows if "WRONG" in r[2] or r[2] == "MISSING"]
    if broken:
        fmt.fail("%d deliverable(s) have a FAIL, not just a TODO" % len(broken))
        print("  Fix these first - a FAIL means the framework caught a")
        print("  contradiction between two things you wrote, and every one")
        print("  of them is something a marker would also notice.")
        print()
        print("  See the detail:  python A2_main/test_all.py %s -v"
              % " ".join(r[0] for r in broken))
    elif worst == 0:
        fmt.ok("every deliverable is complete and verified")
        print("  Now assemble the report:")
        print("      python A2_main/report/assemble.py")
    else:
        fmt.ok("nothing is broken")
        print("  The TODO lines in each deliverable are the work left.")
        print("  Read the WORKPLAN.md in the folder you are picking up.")

    print()
    print("  Suggested order if you are starting: D0(c) first (it must be")
    print("  committed before any agent code), then D4 (it is the biggest")
    print("  job and D0, D6 and D7 all read its numbers).")
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
