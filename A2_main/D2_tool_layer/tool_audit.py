"""
D2(a) - THE TOOL SET, SCORED
=====================================================================
    python A2_main/D2_tool_layer/tool_audit.py

Three jobs, all of them working code:

  1. Score every SHIPPED tool against the three questions, from
     answers_D2.TOOL_AUDIT - and tell you which tools have no row,
     because a tool nobody audited is a tool nobody justified.

  2. Measure LEVER 1 of the D6 cost ledger: the tool block size. Every
     descriptor sits in the prompt prefix, so it is re-sent and
     re-billed on every turn, called or not. Cutting a tool shows up
     here and nowhere else.

  3. Flag the search_notes shape. Class 4's trap tool failed questions
     1 and 2 - "no, nothing fails without it" and "yes, confusable" -
     and it was also the tool that broke the agent. That is not a
     coincidence, it is the argument. This script names any tool of
     yours with the same signature.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, measure, store                         # noqa: E402
from common.template import is_filled                          # noqa: E402
from D2_tool_layer import answers_D2 as A                      # noqa: E402


def shipped_tools(problem="A"):
    from D2_tool_layer import tools
    return sorted(tools.REGISTRY[problem])


def tool_block_tokens(problem="A"):
    """LEVER 1: what the tool definitions cost, per tool and in total.

    This is the B in B*T + D*T(T-1)/2, minus the routing rules and the
    answer format. Linear in turns - it never explodes, but it is paid
    on every single turn of every single run.
    """
    from D2_tool_layer import prompt
    from D2_tool_layer import tools
    per_tool = {}
    for name in shipped_tools(problem):
        descriptor = tools.DESCRIPTORS.get(name)
        text = prompt.format_descriptor(descriptor) if descriptor else ""
        per_tool[name] = {"chars": len(text),
                          "approx_tokens": measure.approx_tokens(text),
                          "described": bool(descriptor)}
    whole_prompt = prompt.build_system_prompt(problem)
    return {
        "per_tool": per_tool,
        "tool_block_tokens": sum(t["approx_tokens"] for t in per_tool.values()),
        "whole_prompt_tokens": measure.approx_tokens(whole_prompt),
        "whole_prompt_chars": len(whole_prompt),
        "estimated": True,
    }


def missing_rows(problem="A"):
    """Tools with no audit row, and audit rows for tools that do not exist."""
    have = set(shipped_tools(problem))
    audited = set(A.TOOL_AUDIT)
    return sorted(have - audited), sorted(audited - have)


def search_notes_shaped():
    """Tools whose answers look like Class 4's trap tool.

    Signature: question 1 answered 'no' AND question 2 answered 'yes'.
    Returns [(tool, why)].
    """
    out = []
    for name, row in A.TOOL_AUDIT.items():
        fails = row.get("fails_without_it")
        confusable = row.get("confusable_with")
        if not (is_filled(fails) and is_filled(confusable)):
            continue
        no_task_fails = str(fails).strip().lower().startswith(("no", "nothing fails"))
        is_confusable = str(confusable).strip().lower().startswith("yes")
        if no_task_fails and is_confusable:
            out.append((name, "fails question 1 AND question 2 - this is the "
                              "search_notes shape"))
    return out


def report(problem="A"):
    fmt.h1("D2(a) - the tool set, scored")

    absent, orphan = missing_rows(problem)
    if absent:
        fmt.todo("no audit row for: %s" % ", ".join(absent))
        print("       A tool nobody audited is a tool nobody justified.")
    if orphan:
        fmt.fail("audit rows for tools that do not exist: %s" % ", ".join(orphan))

    fmt.h2("The three questions")
    rows = []
    for name in shipped_tools(problem):
        row = A.TOOL_AUDIT.get(name, {})
        rows.append((name,
                     row.get("fails_without_it", "-"),
                     row.get("confusable_with", "-"),
                     row.get("cost_when_never_called", "-"),
                     row.get("verdict", "-")))
    fmt.table(["tool", "1 · fails without it?", "2 · confusable?",
               "3 · cost when idle", "verdict"], rows)

    trap = search_notes_shaped()
    if trap:
        fmt.h2("Tools with the search_notes shape")
        for name, why in trap:
            print("  %-24s %s" % (name, why))
        print()
        print("  Class 4's trap tool failed questions 1 and 2 - and it was")
        print("  also the tool that broke the agent. Check whether yours is")
        print("  implicated in a D7 failure. If it is, that is your report")
        print("  paragraph, not a problem.")

    fmt.h2("LEVER 1 - the tool block, re-sent every turn")
    sizes = tool_block_tokens(problem)
    fmt.table(["tool", "chars", "~tokens", "descriptor?"],
              [(n, v["chars"], v["approx_tokens"],
                "yes" if v["described"] else "NO")
               for n, v in sorted(sizes["per_tool"].items(),
                                  key=lambda kv: -kv[1]["approx_tokens"])],
              aligns=["<", ">", ">", "<"])
    print()
    fmt.kv("tool block", "~%d tokens" % sizes["tool_block_tokens"])
    fmt.kv("whole system prompt", "~%d tokens (%d chars)"
           % (sizes["whole_prompt_tokens"], sizes["whole_prompt_chars"]))
    print()
    print("  This is paid on EVERY TURN. It is linear in turns, so it never")
    print("  explodes - but a fat observation compounds, and that is lever 3.")
    print("  Say in the report which of the two dominated your bill.")

    fmt.h2("What we cut, and what we tried before adding")
    if is_filled(A.TOOLS_CUT):
        if A.TOOLS_CUT:
            for cut in A.TOOLS_CUT:
                print("  - %s" % cut.get("tool"))
                print("      added because   : %s" % cut.get("why_added"))
                print("      removed because : %s"
                      % cut.get("observation_that_removed_it"))
        else:
            print("  Nothing cut. That is allowed, but say why in the report -")
            print("  the marks go to the SHORTEST DEFENSIBLE list, and a tool")
            print("  you removed with the observation that removed it earns")
            print("  explicit credit.")
    else:
        print("  %s" % A.TOOLS_CUT)
    print()
    for n in (1, 2, 3, 4):
        print("  move %d: %s" % (n, A.FOUR_MOVES_TRIED.get(n)))
    print()
    fmt.paragraph(A.SHORTEST_DEFENSIBLE_LIST)

    store.save("D2_tool_audit",
               {"tools": shipped_tools(problem),
                "missing_rows": absent,
                "search_notes_shaped": trap,
                "sizes": sizes},
               source="D2/tool_audit.py")
    return sizes


if __name__ == "__main__":
    report()
    raise SystemExit(0)
