"""
D7 - THE TWO FAILURES, REPRODUCED
=====================================================================
    python A2_main/D7_failures/failure_runs.py

Produces the four things D7 asks you to report, for each failure:

  1  THE INSTRUMENTATION THAT FOUND IT. Turns and cost logged per run.
     You cannot report a failure you had no way of noticing.
  2  THE TURN DISTRIBUTION across your whole evaluation set - median,
     worst case, and how many runs hit the step cap. ONE NUMBER IS NOT
     A DISTRIBUTION.
  3  THE FIX, and which layer it belongs in - plus why the other two
     were the wrong place. That judgement is most of the mark.
  4  BEFORE AND AFTER: turns, tokens, cost AND PASS RATE. A step cap
     that stops a runaway also truncates a legitimate long run, so
     show the pass rate did not fall.

Also writes output/D7_turns.json, which D0's s = P^(1/T) reads for T
and which D3 uses to justify its caps from evidence rather than from a
round number.
=====================================================================
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.template import is_filled                          # noqa: E402
from D4_eval_set import eval_runner                            # noqa: E402
from D7_failures import answers_D7 as A                        # noqa: E402
from D7_failures import deletion                               # noqa: E402


# ---------------------------------------------------------------------
# 2 · the turn distribution
# ---------------------------------------------------------------------
def turn_distribution():
    """Across the whole set. Also the evidence D3's caps come from."""
    import config
    results, _queue, _unscripted = eval_runner.run()
    if not results:
        return None
    turns = [r["record"]["turns"] for r in results]
    capped = [r["case_id"] for r in results
              if r["record"]["stopped_by"] == "step_cap"]
    legitimate = [r["record"]["turns"] for r in results if r["passed"]]
    return {
        "runs": len(turns),
        "median_turns": statistics.median(turns),
        "mean_turns": sum(turns) / len(turns),
        "max_turns": max(turns),
        "min_turns": min(turns),
        "worst_legitimate_turns": max(legitimate) if legitimate else None,
        "hit_step_cap": len(capped),
        "capped_cases": capped,
        "step_cap": config.MAX_TURNS,
        "budget_ceiling": config.MAX_TOKENS_PER_RUN,
        "histogram": {t: turns.count(t) for t in sorted(set(turns))},
    }


# ---------------------------------------------------------------------
# 4 · before and after, on the whole set
# ---------------------------------------------------------------------
def _set_summary():
    results, _q, _u = eval_runner.run()
    return eval_runner.summarise(results) if results else None


def before_after(name, case_id, loop_script=False, **options):
    """One failure: the working agent, and the working agent minus X."""
    from D1_agent_loop.agent import run_case
    import config

    before_run = run_case(case_id, problem=config.PROBLEM)
    before_set = _set_summary()

    def _do():
        with deletion.deletion(name, **options):
            run = run_case(case_id, problem=config.PROBLEM)
            whole = _set_summary()
        return run, whole

    if loop_script:
        with deletion.scripted_as(case_id,
                                  deletion.looping_script(case_id)):
            after_run, after_set = _do()
    else:
        after_run, after_set = _do()

    restored, detail = deletion.verify_restored(case_id, name, **options)

    return {
        "deletion": name,
        "layer": deletion.LAYERS.get(name),
        "case": case_id,
        "before": _run_row(before_run),
        "after": _run_row(after_run),
        "before_set": before_set,
        "after_set": after_set,
        "restored": restored,
        "restored_detail": detail,
    }


def _run_row(record):
    return {"turns": record["turns"],
            "tool_calls": len(record["evidence"]),
            "tokens": record["tokens_in"] + record["tokens_out"],
            "cost_usd": record["cost_usd"],
            "decision": record["decision"],
            "stopped_by": record["stopped_by"]}


# ---------------------------------------------------------------------
def _print_failure(title, data, reasoning):
    fmt.h2(title)
    fmt.kv("deletion", "%s   (layer: %s)" % (data["deletion"], data["layer"]))
    fmt.kv("case", data["case"])
    print()

    b, a = data["before"], data["after"]
    fmt.table(["", "turns", "tool calls", "tokens", "cost US$", "decision",
               "stopped by"],
              [("before", b["turns"], b["tool_calls"], b["tokens"],
                "%.5f" % b["cost_usd"], b["decision"], b["stopped_by"]),
               ("after", a["turns"], a["tool_calls"], a["tokens"],
                "%.5f" % a["cost_usd"], a["decision"], a["stopped_by"])],
              aligns=["<", ">", ">", ">", ">", "<", "<"])

    print()
    print("  1 · THE INSTRUMENTATION THAT FOUND IT")
    spend = a["tokens"] / max(1, b["tokens"])
    print("      Turns and cost logged per run. The broken run cost %.1fx"
          % spend)
    print("      more and answered %r." % a["decision"])
    if a["decision"] == b["decision"] and a["stopped_by"] is None:
        print("      THE SAME ANSWER AS THE WORKING AGENT, and nothing raised")
        print("      an exception. A pass-rate table alone would show this as")
        print("      a clean pass. It is only visible because turns and cost")
        print("      were counted WHILE THE RUN HAPPENED.")

    print()
    print("  4 · BEFORE AND AFTER, on the whole set")
    if data["before_set"] and data["after_set"]:
        bs, as_ = data["before_set"], data["after_set"]
        fmt.table(["", "pass rate", "trials", "median turns", "cost US$"],
                  [("before", "%.1f%%" % (bs["pass_rate"] * 100), bs["trials"],
                    bs["median_turns"], "%.5f" % bs["cost_usd"]),
                   ("after", "%.1f%%" % (as_["pass_rate"] * 100), as_["trials"],
                    as_["median_turns"], "%.5f" % as_["cost_usd"])],
                  aligns=["<", ">", ">", ">", ">"])
        if as_["pass_rate"] < bs["pass_rate"]:
            print("      Pass rate FELL when X was removed - the guard was")
            print("      doing correctness work, not only cost work.")
    print()
    print("  restoring X: %s" % ("recovered the behaviour"
                                 if data["restored"] else "DID NOT RECOVER"))
    print("      %s" % data["restored_detail"])
    if not data["restored"]:
        print("      D7 requires that putting X back recovers the behaviour.")
        print("      If it does not, the deletion changed something else too")
        print("      and the diagnosis does not hold.")

    print()
    print("  3 · THE FIX, AND WHY THE OTHER TWO LAYERS WERE WRONG")
    for key in ("fix", "why_this_layer", "why_not_code", "why_not_tool",
                "why_not_prompt"):
        if key in reasoning:
            print("      %-16s %s" % (key + ":", reasoning[key]))


def report():
    fmt.h1("D7 - two reproduced failures")

    # -- 2 · the distribution, first, because everything cites it ------
    dist = turn_distribution()
    fmt.h2("2 · The turn distribution - one number is not a distribution")
    if not dist:
        fmt.fail("no runs to measure")
        return None
    fmt.kv("runs", dist["runs"])
    fmt.kv("median turns", dist["median_turns"])
    fmt.kv("worst case turns", dist["max_turns"])
    fmt.kv("worst LEGITIMATE run", dist["worst_legitimate_turns"])
    fmt.kv("hit the step cap", "%d  %s" % (dist["hit_step_cap"],
                                           dist["capped_cases"] or ""))
    fmt.kv("step cap in force", dist["step_cap"])
    print()
    fmt.table(["turns", "runs"],
              [(t, n) for t, n in dist["histogram"].items()],
              aligns=[">", ">"])
    print()
    print("  SET YOUR CAPS FROM THIS, not from a round number. Median %s and"
          % dist["median_turns"])
    print("  a worst legitimate run of %s make a cap of %s defensible; a cap"
          % (dist["worst_legitimate_turns"], dist["step_cap"]))
    print("  of 30 would be decoration. Say in the report where yours came")
    print("  from.")
    store.save("D7_turns", dist, source="D7/failure_runs.py")

    # -- failure 1 -----------------------------------------------------
    case = A.FAILURE_1.get("case_id")
    if not is_filled(case):
        case = _default_case()
    if case:
        data1 = before_after("dedup", case, loop_script=True)
        _print_failure("Failure 1 · loop control (REQUIRED)", data1, A.FAILURE_1)
        print()
        print("      Note what did NOT fire. The step cap bounds the damage;")
        print("      it does not detect the fault, and it names no cause when")
        print("      it does stop things. The budget ceiling is the same. Only")
        print("      the code layer REMEMBERS what was already done - and a")
        print("      prompt fix cannot be relied on, because the model is the")
        print("      thing that forgot.")
    else:
        data1 = None
        fmt.fail("no scripted case to demonstrate failure 1 on")

    # -- failure 2 -----------------------------------------------------
    name2 = A.FAILURE_2.get("deletion")
    data2 = None
    if is_filled(name2) and name2 in deletion.available():
        if deletion.LAYERS.get(name2) == "code":
            fmt.fail("Failure 2 is in the CODE layer (%s)" % name2)
            print("  D7 requires the second failure to sit in the TOOL")
            print("  INTERFACE or the PROMPT, not in loop control again.")
        else:
            case2 = A.FAILURE_2.get("case_id")
            case2 = case2 if is_filled(case2) else case
            data2 = before_after(name2, case2)
            _print_failure("Failure 2 · %s" % deletion.LAYERS.get(name2),
                           data2, A.FAILURE_2)
    else:
        fmt.h2("Failure 2 · a different layer")
        fmt.todo("FAILURE_2['deletion'] not chosen",
                 "must be one of: %s"
                 % ", ".join(n for n in deletion.available()
                             if deletion.LAYERS[n] != "code"))

    store.save("D7_failures", {"distribution": dist,
                               "failure_1": data1, "failure_2": data2},
               source="D7/failure_runs.py")
    return {"distribution": dist, "failure_1": data1, "failure_2": data2}


def _default_case():
    from D4_eval_set import scripts
    return "CLM-8842" if "CLM-8842" in scripts.SCRIPTS else (
        sorted(scripts.SCRIPTS)[0] if scripts.SCRIPTS else None)


if __name__ == "__main__":
    report()
    raise SystemExit(0)
