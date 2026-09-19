"""
D4 - RUN THE EVALUATION SET
=====================================================================
    python A2_main/D4_eval_set/eval_runner.py             # scripted cases
    python A2_main/D4_eval_set/eval_runner.py --all       # every case

Runs the set the way D4 specifies and writes output/D4_eval.json,
which D0 (the s = P^(1/T) arithmetic) and D6 (layer 2) both read. One
measurement, one file, one number in the report.

WHAT IT ENFORCES, beyond just running things:

  ISOLATION      every case starts from a clean state. The scaffold's
                 run_case() builds its own guardrails, transcript and
                 backend per run, so this is already true - and the
                 script re-runs one case twice to prove it rather than
                 asserting it.
  TRIAL POLICY   ordinary cases get 1 trial, NEGATIVE cases get 3.
                 Negatives are the ones that flip between runs, and a
                 single trial cannot tell a real refusal from a lucky
                 one.
  MIXED GRADERS  the code check produces the number; the judgement
                 queue is built, not answered. `must_record` items are
                 written in English and a substring match would be
                 theatre, not a check.

EVERY PASS RATE IS PRINTED WITH ITS TRIAL COUNT. A pass rate without
one is not a measurement.
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
from D0_why_an_agent import reliability                        # noqa: E402
from D4_eval_set import answers_D4 as A                        # noqa: E402

NEGATIVE_DECISIONS = ("escalate", "request_document")


def trials_for(expected):
    ordinary = A.TRIALS_ORDINARY if is_filled(A.TRIALS_ORDINARY) else 1
    negative = A.TRIALS_NEGATIVE if is_filled(A.TRIALS_NEGATIVE) else 3
    if expected and expected.get("expected_decision") in NEGATIVE_DECISIONS:
        return negative
    return ordinary


def runnable_cases(every=False):
    """Cases we can actually run right now."""
    from D4_eval_set import scripts
    import config
    from D4_eval_set.harness import load_cases, load_key
    key = load_key(config.PROBLEM)
    cases = [c for c in load_cases(config.PROBLEM) if c in key]
    if every or config.BACKEND == "live":
        return cases, []
    have = [c for c in cases if c in scripts.SCRIPTS]
    return have, [c for c in cases if c not in scripts.SCRIPTS]


def run(every=False, on_progress=None, case_ids=None):
    """Run the evaluation set.

    `on_progress`, if given, is called as
        on_progress(done, total, case_id, trial, trials_for_case, record)
    after every trial. Used by the live battery progress bar.

    `case_ids`, if given, restricts the run to that ordered subset
    (still present in the answer key). Optional; default is the full set.
    """
    import config
    from D1_agent_loop.agent import run_case
    from D4_eval_set.harness import (code_check, load_key,
                                 prepare_judgement_check)

    key = load_key(config.PROBLEM)
    cases, unscripted = runnable_cases(every)
    if case_ids is not None:
        want = set(case_ids)
        missing = [c for c in case_ids if c not in key]
        if missing:
            raise SystemExit("unknown case_ids: %s" % ", ".join(missing))
        cases = [c for c in case_ids if c in want and c in key]
    results, queue = [], []

    plan = [(cid, trials_for(key[cid])) for cid in cases]
    total = sum(n for _cid, n in plan)
    done = 0

    for cid, n_trials in plan:
        expected = key[cid]
        for trial in range(1, n_trials + 1):
            record = run_case(cid, problem=config.PROBLEM)
            passed, fails = code_check(record, expected)
            results.append({"case_id": cid, "trial": trial, "passed": passed,
                            "fails": fails, "record": record,
                            "family": expected.get("family"),
                            "negative": expected.get("expected_decision")
                            in NEGATIVE_DECISIONS})
            if trial == 1:
                queue.append(prepare_judgement_check(record, expected))
            done += 1
            if on_progress is not None:
                on_progress(done, total, cid, trial, n_trials, record)
    return results, queue, unscripted


def isolation_holds(case_id):
    """Two runs of the same case from a clean state must be identical."""
    import config
    from D1_agent_loop.agent import run_case
    a = run_case(case_id, problem=config.PROBLEM)
    b = run_case(case_id, problem=config.PROBLEM)
    drop = ("seconds",)
    return ({k: v for k, v in a.items() if k not in drop} ==
            {k: v for k, v in b.items() if k not in drop})


def summarise(results):
    if not results:
        return {"trials": 0}
    turns = [r["record"]["turns"] for r in results]
    passed = sum(1 for r in results if r["passed"])
    negatives = [r for r in results if r["negative"]]
    neg_passed = sum(1 for r in negatives if r["passed"])

    by_family = {}
    for r in results:
        fam = r["family"] or "(none)"
        row = by_family.setdefault(fam, {"trials": 0, "passed": 0})
        row["trials"] += 1
        row["passed"] += 1 if r["passed"] else 0

    return {
        "trials": len(results),
        "cases": len({r["case_id"] for r in results}),
        "passed": passed,
        "pass_rate": passed / len(results),
        "negative_trials": len(negatives),
        "negative_pass_rate": (neg_passed / len(negatives)) if negatives else None,
        "median_turns": statistics.median(turns),
        "max_turns": max(turns),
        "hit_step_cap": sum(1 for r in results
                            if r["record"]["stopped_by"] == "step_cap"),
        "tokens_in": sum(r["record"]["tokens_in"] for r in results),
        "tokens_out": sum(r["record"]["tokens_out"] for r in results),
        "cost_usd": sum(r["record"]["cost_usd"] for r in results),
        "by_family": by_family,
        "per_case": [{"case_id": r["case_id"], "trial": r["trial"],
                      "turns": r["record"]["turns"], "passed": r["passed"],
                      "family": r["family"], "negative": r["negative"],
                      "decision": r["record"].get("decision"),
                      "trigger": r["record"].get("trigger"),
                      "reason": (r["record"].get("reason") or "")[:240],
                      "evidence": r["record"].get("evidence"),
                      "stopped_by": r["record"].get("stopped_by"),
                      "fails": r.get("fails") or []}
                     for r in results],
        "weak_step_candidates": reliability.weak_step_candidates(results),
        "decision_counts": _decision_counts(results),
    }


def _decision_counts(results):
    from collections import Counter
    return dict(Counter((r["record"].get("decision") or "(none)")
                        for r in results))


def report(every=False):
    import config
    fmt.h1("D4 - the evaluation set")
    print("  %s" % config.summary().splitlines()[0])

    results, queue, unscripted = run(every)
    if not results:
        fmt.fail("nothing ran")
        print("  No case has both a label and a script. Write a script in")
        print("  D4_eval_set/scripts.py, or set BACKEND='live'.")
        return None

    s = summarise(results)

    fmt.h2("Size of the set")
    fmt.kv("cases with a label", s["cases"])
    fmt.kv("negative cases", len({r["case_id"] for r in results if r["negative"]}))
    fmt.kv("trials run", s["trials"])
    if s["cases"] < 30:
        fmt.todo("D4 wants 30-50 cases; %d are runnable" % s["cases"])
        print("       A 10-case set cannot tell two policies apart. Size is")
        print("       what makes the number mean something.")
    if unscripted:
        fmt.todo("%d labelled case(s) have no script yet" % len(unscripted))
        print("       %s" % ", ".join(unscripted[:12]))

    fmt.h2("Results  (every pass rate carries its trial count)")
    fmt.kv("pass rate", "%.1f%%  (%d of %d trials)"
           % (s["pass_rate"] * 100, s["passed"], s["trials"]))
    if s["negative_pass_rate"] is not None:
        fmt.kv("negative pass rate", "%.1f%%  (%d trials)"
               % (s["negative_pass_rate"] * 100, s["negative_trials"]))
    fmt.kv("median turns", s["median_turns"])
    fmt.kv("worst case turns", s["max_turns"])
    fmt.kv("hit the step cap", s["hit_step_cap"])
    fmt.kv("cost", "US$%.4f" % s["cost_usd"])

    fmt.h2("By negative-case family")
    fmt.table(["family", "trials", "passed", "rate"],
              [(k, v["trials"], v["passed"],
                "%.0f%%" % (v["passed"] / v["trials"] * 100))
               for k, v in sorted(s["by_family"].items())],
              aligns=["<", ">", ">", ">"])

    failures = [r for r in results if not r["passed"]]
    if failures:
        fmt.h2("Failed trials - each is either a bug or a wrong label")
        for r in failures:
            print("  %-12s trial %d  [%s]"
                  % (r["case_id"], r["trial"], r["family"]))
            for f in r["fails"]:
                print("      %s" % f)
        print()
        print("  Before you fix the agent, ask whether the LABEL is right.")
        print("  Could you justify the label to someone who had never seen")
        print("  your agent's output, using only Appendix A's routing table?")
        print("  If yes, the agent is wrong. If no, the label is.")

    fmt.h2("Isolation")
    probe = results[0]["case_id"]
    held = isolation_holds(probe)
    (fmt.ok if held else fmt.fail)(
        "two clean runs of %s are %s" % (probe, "identical" if held else
                                         "DIFFERENT - state is leaking"))

    fmt.h2("The judgement queue - built, not answered")
    print("  %d item(s). A person or a second model rules on each." % len(queue))
    print("  graded by: %s" % A.JUDGEMENT_GRADER)
    print()
    print("  These are written in English and a substring match would be")
    print("  theatre, not a check. If you automate it with a model, say so:")
    print("  a model grading a model is a claim that needs defending.")

    store.save("D4_eval", s, source="D4/eval_runner.py")
    store.save("D4_judgement", queue, source="D4/eval_runner.py")
    print()
    print("  Wrote output/D4_eval.json and output/D4_judgement.json.")
    print("  D0's arithmetic and D6's layer 2 both read the first one.")
    return s


if __name__ == "__main__":
    report(every="--all" in sys.argv)
    raise SystemExit(0)
