#!/usr/bin/env python3
"""
A2_main - WHAT CODE IS STILL TO BE WRITTEN
=====================================================================
    python A2_main/code_todo.py           # everything, grouped by D
    python A2_main/code_todo.py D3        # just one deliverable
    python A2_main/code_todo.py --files   # which file holds what

The companion to test_all.py. That one reports the DECISIONS still to
be made (the TEMPLATE slots in each answers_Dx.py); this one reports
the CODE still to be written (the TODO(Dn/topic) markers in the
implementation).

Between them they are the whole work list, and neither can go stale,
because both are read out of the source rather than kept beside it.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.bootstrap import init, A2_MAIN
init()

from common import codemap, fmt                                # noqa: E402

WHERE = [
    ("D1", "D1_agent_loop/agent.py", "the ReAct loop itself"),
    ("D2", "D2_tool_layer/tools.py", "tool implementations + descriptors"),
    ("D2", "D2_tool_layer/prompt.py", "descriptors -> the system prompt"),
    ("D3", "D3_guardrails/guardrails.py", "step cap, budget, dedup, gate"),
    ("D3", "config.py", "the limits those guardrails run at"),
    ("D4", "D4_eval_set/scripts.py", "the scripted moves, one per case"),
    ("D4", "D4_eval_set/harness.py", "graders and the judgement queue"),
    ("D4", "data/make_fixtures_A.py", "the fixture generator"),
    ("D5", "D5_model_battery/backends.py", "scripted and live backends"),
]


def main(argv):
    wanted = [a.upper() for a in argv[1:] if not a.startswith("-")]

    if "--files" in argv:
        fmt.h1("Where the implementation lives")
        fmt.table(["", "file", "what it is"], WHERE)
        print()
        print("  Each deliverable owns the code it is marked on, so \"what is")
        print("  left for D3\" is a folder rather than a grep.")
        return 0

    groups = codemap.by_deliverable(A2_MAIN)
    fmt.h1("Code still to be written")
    print("  Markers found in the implementation. The DECISIONS still to")
    print("  be made are a separate list:  python A2_main/test_all.py")

    total = 0
    for deliverable in sorted(groups):
        if wanted and deliverable not in wanted:
            continue
        rows = groups[deliverable]
        total += len(rows)
        fmt.h2("%s - %d item(s)" % (deliverable, len(rows)))
        for topic, path, line, text in rows:
            print("  %s:%d" % (path, line))
            print("      [%s] %s" % (topic, text))
            print()

    if not total:
        fmt.ok("no TODO markers left in the implementation")
        print("  That is not the same as finished - check the TEMPLATE slots")
        print("  too:  python A2_main/test_all.py")
        return 0

    fmt.h1("Summary")
    fmt.table(["", "code items"],
              [(d, len(groups[d])) for d in sorted(groups)
               if not wanted or d in wanted],
              aligns=["<", ">"])
    print()
    print("  %d marker(s) outstanding." % total)
    print()
    print("  Suggested order, because things are waiting on each other:")
    print("    1. D4/scripts.py   - 39 more scripts. D3's hostile-text cases,")
    print("                         D5(a)'s reproducible run and D0's \"the")
    print("                         steps vary\" claim are all blocked on it.")
    print("    2. D5/backends.py  - real token counts, before the live")
    print("                         battery, or D6 layer 1 is an estimate")
    print("                         wearing the label \"measured\".")
    print("    3. config.py       - the caps, once D7 has printed the turn")
    print("                         distribution they come from.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
