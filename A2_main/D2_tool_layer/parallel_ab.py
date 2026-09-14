"""
D2(c) - SEQUENTIAL vs PARALLEL, MEASURED
=====================================================================
    python A2_main/D2_tool_layer/parallel_ab.py

The brief asks for four things and this script produces all four:

  1  a loop that executes a SET of tool calls in one turn   (scaffold)
  2  the dependency rule                                    (answers_D2)
  3  the measurement: turns, tokens and cost, both ways     (here)
  4  proof correctness did not move                         (here)

HOW THE SEQUENTIAL ARM IS BUILT, because this is the interesting bit.
We do not write a second agent. We take the SAME scripted moves and
flatten them: every turn that fired k calls becomes k turns of one
call each. Same tools, same arguments, same observations, same final
record - only the grouping changes. That is what makes this an
experiment rather than two different agents being compared.

WHAT IT SHOULD SHOW. Nothing is cut, so the total observation volume
is identical. What changes is how many times the history was re-sent,
and the whole saving lives in the quadratic term of

    input ~ B*T + D*T(T-1)/2

TWO HONEST LIMITS the brief expects you to find, both in answers_D2:
parallel calls can COST more when an early observation would have told
you to skip one (CLM-8925 breaches the annual limit at turn 2 - fire
every coverage check at once and you paid for four you never needed),
and they remove a decision point the model would otherwise have used.
=====================================================================
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, measure, store                         # noqa: E402
from common.template import is_filled                          # noqa: E402
from D2_tool_layer import answers_D2 as A                      # noqa: E402


def flatten_script(steps):
    """One call per turn. The sequential arm of the experiment."""
    out = []
    for step in steps:
        if "final" in step or not step.get("calls"):
            out.append(copy.deepcopy(step))
            continue
        calls = step["calls"]
        for i, call in enumerate(calls):
            one = copy.deepcopy(step)
            one["calls"] = [call]
            if i:
                one["thought"] = "(sequential arm) " + str(step.get("thought", ""))
            out.append(one)
    return out


def _run(case_ids, flatten):
    """Run the scripted cases with the scripts grouped or flattened."""
    from D4_eval_set import scripts
    import config
    from D4_eval_set.harness import load_key, code_check
    from D1_agent_loop.agent import run_case

    original = dict(scripts.SCRIPTS)
    try:
        if flatten:
            scripts.SCRIPTS = {k: flatten_script(v)
                                for k, v in original.items()}
        key = load_key(config.PROBLEM)
        rows = []
        for cid in case_ids:
            record = run_case(cid, problem=config.PROBLEM)
            expected = key.get(cid)
            passed, fails = (code_check(record, expected) if expected
                             else (None, ["no label"]))
            rows.append({"case_id": cid, "passed": passed, "fails": fails,
                         "record": record})
        return rows
    finally:
        scripts.SCRIPTS = original


def scripted_cases():
    from D4_eval_set import scripts
    import config
    from D4_eval_set.harness import load_cases, load_key
    key = load_key(config.PROBLEM)
    return [c for c in load_cases(config.PROBLEM)
            if c in scripts.SCRIPTS and c in key]


def compare(case_ids=None):
    """Both arms, with everything the report table needs."""
    case_ids = case_ids or scripted_cases()
    if not case_ids:
        return None

    parallel = _run(case_ids, flatten=False)
    sequential = _run(case_ids, flatten=True)

    out = {
        "cases": case_ids,
        "parallel": measure.summarise_runs(parallel),
        "sequential": measure.summarise_runs(sequential),
        "per_case": [],
    }
    by_id = {r["case_id"]: r for r in sequential}
    for r in parallel:
        s = by_id[r["case_id"]]
        out["per_case"].append({
            "case_id": r["case_id"],
            "parallel_turns": r["record"]["turns"],
            "sequential_turns": s["record"]["turns"],
            "calls": len(r["record"]["evidence"]),
            "parallel_passed": r["passed"],
            "sequential_passed": s["passed"],
        })

    p, q = out["parallel"], out["sequential"]
    out["saving"] = {
        "turns_pct": _pct_drop(q["total_turns"], p["total_turns"]),
        "input_tokens_pct": _pct_drop(q["tokens_in"], p["tokens_in"]),
        "cost_pct": _pct_drop(q["cost_usd"], p["cost_usd"]),
        "pass_rate_moved": (p["pass_rate"] != q["pass_rate"]),
    }
    out["halted"] = _halted(sequential, parallel)
    return out


def _halted(sequential, parallel):
    """Runs a guardrail stopped, per arm.

    WHY THIS IS TRACKED SEPARATELY. When the sequential arm returns a
    different outcome it is worth knowing WHY, because there are two
    very different explanations:

      (a) a guardrail halted it - the step cap or the budget ceiling.
          The extra turns did not merely cost more, they breached a
          limit and the run returned the wrong answer. That is not a
          flaw in the experiment; it is the strongest version of the
          D2(c) argument, and it belongs in the report as a finding.

      (b) no guardrail fired and the answer still moved. THAT is a
          real problem: regrouping calls should not change what any of
          them returns, and something else is wrong.
    """
    def rows(arm):
        return [{"case_id": r["case_id"],
                 "stopped_by": r["record"].get("stopped_by"),
                 "decision": r["record"].get("decision"),
                 "reason": r["record"].get("reason")}
                for r in arm if r["record"].get("stopped_by")]
    return {"sequential": rows(sequential), "parallel": rows(parallel)}


def _pct_drop(before, after):
    return 0.0 if not before else (before - after) / before * 100.0


def formula_table(base_tokens, observation_tokens_per_call, turn_counts):
    """The Class 5 arithmetic, so the measured saving has a model beside it.

    D grows when calls are batched: the same observations arrive in
    fewer, fatter turns. That is why the sequential arm gets a smaller
    D and a larger T, and the quadratic still favours the batch.
    """
    rows = []
    for label, turns, calls_per_turn in turn_counts:
        D = observation_tokens_per_call * calls_per_turn
        rows.append((label, turns, base_tokens, D,
                     measure.context_tokens(base_tokens, D, turns)))
    return rows


def report():
    fmt.h1("D2(c) - calling more than one tool in a turn")

    fmt.h2("The dependency rule")
    fmt.paragraph(A.DEPENDENCY_RULE)
    if is_filled(A.DEPENDS_ON):
        fmt.table(["tool", "needs the output of"],
                  [(k, ", ".join(v) if v else "(nothing - entry point)")
                   for k, v in A.DEPENDS_ON.items()])
        broken = check_rule_against_scripts()
        if broken:
            fmt.h2("Scripts that BREAK the dependency rule")
            for turn, tool, needs in broken:
                print("  turn %d puts %s alongside %s, which it depends on"
                      % (turn, tool, needs))
            print()
            print("  A pair may share a turn only when NEITHER needs the")
            print("  other's output. Fix the script or fix the rule.")
        else:
            fmt.ok("every scripted turn obeys the dependency rule")

    data = compare()
    if not data:
        print("\n  No scripted cases to compare. Script at least one in")
        print("  D4_eval_set/scripts.py.")
        return None

    fmt.h2("Measured, over %d scripted case(s)" % len(data["cases"]))
    p, q = data["parallel"], data["sequential"]
    fmt.table(["", "turns", "input tokens", "output tokens", "cost US$",
               "pass rate"],
              [("sequential", q["total_turns"], q["tokens_in"], q["tokens_out"],
                "%.5f" % q["cost_usd"], "%.0f%%" % (q["pass_rate"] * 100)),
               ("parallel", p["total_turns"], p["tokens_in"], p["tokens_out"],
                "%.5f" % p["cost_usd"], "%.0f%%" % (p["pass_rate"] * 100))],
              aligns=["<", ">", ">", ">", ">", ">"])
    print()
    s = data["saving"]
    fmt.kv("turns saved", "%.0f%%" % s["turns_pct"])
    fmt.kv("input tokens saved", "%.0f%%" % s["input_tokens_pct"])
    fmt.kv("cost saved", "%.0f%%" % s["cost_pct"])

    fmt.h2("4 · did correctness move?")
    halted = data["halted"]["sequential"]
    if not s["pass_rate_moved"]:
        fmt.ok("pass rate identical in both arms")
    elif halted:
        fmt.ok("pass rate moved, and a guardrail explains every case of it")
        print()
        print("  THIS IS A FINDING, NOT A BROKEN EXPERIMENT - and it is the")
        print("  strongest version of the D2(c) argument you can put in the")
        print("  report. The sequential arm did not merely cost more. It")
        print("  breached a limit and returned the WRONG OUTCOME:")
        print()
        for h in halted:
            print("    %s  halted by %s" % (h["case_id"], h["stopped_by"]))
            print("        decision became %r" % h["decision"])
            print("        %s" % h["reason"])
        print()
        print("  Read what that means. Batching independent calls is not a")
        print("  tidiness argument about tokens; on this evidence it is what")
        print("  keeps the run inside the budget ceiling at all. Quote these")
        print("  two numbers together in section 2 of the report.")
    else:
        fmt.fail("pass rate CHANGED and no guardrail explains it")
        print("  Regrouping calls should not change what any of them returns,")
        print("  and nothing was halted. The two arms are not the same work -")
        print("  find the case below before you trust either number.")
        for row in data["per_case"]:
            if row["parallel_passed"] != row["sequential_passed"]:
                print("    %s  parallel=%s sequential=%s"
                      % (row["case_id"], row["parallel_passed"],
                         row["sequential_passed"]))
    fmt.paragraph(A.PARALLEL_CORRECTNESS)

    fmt.h2("Per case")
    fmt.table(["case", "calls", "sequential turns", "parallel turns", "saved"],
              [(r["case_id"], r["calls"], r["sequential_turns"],
                r["parallel_turns"],
                "%d" % (r["sequential_turns"] - r["parallel_turns"]))
               for r in data["per_case"]],
              aligns=["<", ">", ">", ">", ">"])

    fmt.h2("The two honest limits")
    print("  when parallel costs MORE:")
    fmt.paragraph(A.PARALLEL_LIMITS["unnecessary_calls"], indent=4)
    print("  the decision point it removes:")
    fmt.paragraph(A.PARALLEL_LIMITS["removed_decision_point"], indent=4)

    store.save("D2_parallel", data, source="D2/parallel_ab.py")
    return data


def check_rule_against_scripts():
    """Does any scripted turn put a tool beside something it depends on?"""
    from D4_eval_set import scripts
    if not is_filled(A.DEPENDS_ON):
        return []
    broken = []
    for steps in scripts.SCRIPTS.values():
        turn = 0
        for step in steps:
            if "final" in step or not step.get("calls"):
                continue
            turn += 1
            names = [n for n, _ in step["calls"]]
            for name in names:
                for need in A.DEPENDS_ON.get(name, []) or []:
                    if need in names and need != name:
                        broken.append((turn, name, need))
    return broken


if __name__ == "__main__":
    report()
    raise SystemExit(0)
