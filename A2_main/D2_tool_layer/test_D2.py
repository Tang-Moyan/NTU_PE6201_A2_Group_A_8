"""
D2 - TEST SCRIPT
=====================================================================
    python A2_main/D2_tool_layer/test_D2.py

Checks all three parts and runs both experiments. The two checks worth
knowing about:

  - EVERY shipped tool needs an audit row and a six-field descriptor.
    A tool the model can call but was never told about is a bug you
    will spend an evening on.
  - The dependency rule is checked AGAINST THE SCRIPTS. A rule nobody
    enforces is documentation; this one is enforced.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D2_tool_layer import answers_D2 as A                      # noqa: E402
from D2_tool_layer import descriptor_ab, parallel_ab, tool_audit   # noqa: E402

SIX_FIELDS = ("name", "purpose", "when", "args", "returns", "failure")


def test_audit(c):
    absent, orphan = tool_audit.missing_rows()
    c.require("every shipped tool has an audit row", not absent,
              "no row for: %s" % ", ".join(absent), soft=True, ok_detail="")
    c.require("no audit rows for tools that do not exist", not orphan,
              "orphans: %s" % ", ".join(orphan), ok_detail="")

    trap = tool_audit.search_notes_shaped()
    if trap:
        c.todo("a tool with the search_notes shape",
               ", ".join(n for n, _ in trap) +
               " - fails questions 1 and 2. Cut it, or say in the report why "
               "it stays")
    else:
        c.ok("no tool fails both question 1 and question 2")


def test_descriptors(c):
    from D2_tool_layer import tools
    problem = "A"
    undescribed, incomplete = [], []
    for name in sorted(tools.REGISTRY[problem]):
        d = tools.DESCRIPTORS.get(name)
        if not d:
            undescribed.append(name)
            continue
        gaps = [f for f in SIX_FIELDS if not d.get(f) and d.get(f) != {}]
        if gaps:
            incomplete.append("%s missing %s" % (name, "/".join(gaps)))
    c.require("every callable tool has a descriptor", not undescribed,
              "no descriptor: %s" % ", ".join(undescribed))
    c.require("every descriptor has all six fields", not incomplete,
              "; ".join(incomplete))

    c.require("at least two poka-yoke moves", len(A.POKA_YOKE) >= 2,
              "got %d" % len(A.POKA_YOKE))
    for i, py in enumerate(A.POKA_YOKE, 1):
        if is_filled(py.get("makes_impossible")):
            text = str(py["makes_impossible"]).lower()
            weak = [w for w in ("discourage", "remind", "encourage", "try to",
                                "should not") if w in text]
            c.require("poka-yoke %d states an impossibility" % i, not weak,
                      "reads like a nudge (%s) - state what it makes "
                      "IMPOSSIBLE, not what it discourages" % ", ".join(weak))


def test_descriptor_experiment(c):
    tool = A.DESCRIPTOR_EXPERIMENT_TOOL
    if not is_filled(tool):
        c.todo("D2(b) experiment tool chosen")
        return
    from D2_tool_layer import tools
    c.require("the experiment tool exists", tool in tools.REGISTRY["A"],
              "%r is not in the registry" % (tool,))
    c.require("DESCRIPTOR_V1 written", is_filled(A.DESCRIPTOR_V1),
              "the deliberately worse version is the control arm", soft=True)
    c.require("v1_return() written", descriptor_ab.v1_return_written(),
              "D2(b) asks for a descriptor AND a return shape", soft=True)


def test_parallel(c):
    broken = parallel_ab.check_rule_against_scripts()
    c.require("scripts obey the dependency rule", not broken,
              "; ".join("turn %d: %s beside %s" % b for b in broken))

    data = parallel_ab.compare()
    if not data:
        c.fail("no scripted case to run the D2(c) experiment on")
        return
    p, q = data["parallel"], data["sequential"]

    c.require("parallel really does use fewer turns",
              p["total_turns"] < q["total_turns"],
              "parallel %d turns vs sequential %d - if these are equal your "
              "loop is not batching anything"
              % (p["total_turns"], q["total_turns"]))

    halted = data["halted"]["sequential"]
    if p["pass_rate"] == q["pass_rate"]:
        c.ok("4 - correctness did not move",
             "both arms %.0f%%" % (p["pass_rate"] * 100))
    elif halted:
        # Not a broken experiment. The extra turns breached a limit, and
        # that is the strongest form of the D2(c) argument.
        c.ok("4 - correctness moved, and a guardrail explains it",
             "sequential halted by %s on %s - report this as a finding"
             % (halted[0]["stopped_by"],
                ", ".join(h["case_id"] for h in halted)))
    else:
        c.fail("4 - correctness moved with no guardrail to explain it",
               "parallel %.0f%% vs sequential %.0f%% - regrouping calls "
               "should not change what they return"
               % (p["pass_rate"] * 100, q["pass_rate"] * 100))

    c.ok("measured saving",
         "%.0f%% turns, %.0f%% input tokens"
         % (data["saving"]["turns_pct"], data["saving"]["input_tokens_pct"]))


def main():
    c = Checker("D2 - the tool layer")
    test_audit(c)
    test_descriptors(c)
    test_descriptor_experiment(c)
    test_parallel(c)
    c.templates(A, "D2 answers filled")
    code = c.finish()
    print()
    print("  Full reports:")
    print("    python A2_main/D2_tool_layer/tool_audit.py       (D2a)")
    print("    python A2_main/D2_tool_layer/descriptor_ab.py    (D2b)")
    print("    python A2_main/D2_tool_layer/parallel_ab.py      (D2c)")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
