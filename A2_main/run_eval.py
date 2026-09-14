#!/usr/bin/env python3
"""
PE6201 · A2 scaffold — ENTRY POINT
====================================================================
    python3 run_eval.py              run every SCRIPTED case
    python3 run_eval.py CLM-8842     run one case, showing every turn
    python3 run_eval.py --all        run every case in the work queue
    python3 run_eval.py --prompt     print what the model is told, and stop

THIS IS WHAT A MARKER RUNS. Clone, `python3 run_eval.py`, numbers come
back. No key, no network, no arguments. If that does not work on a
clean machine, D5(a) has failed and Technical Execution is capped.

Test it the way a marker will: clone your own repository into a fresh
folder and run it there. "Works on my laptop" has caught out every
cohort so far.
====================================================================
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.bootstrap import init
init()

import config                                                  # noqa: E402
from D4_eval_set.harness import (load_cases, load_key,          # noqa: E402
                                 report, run_set)
from D4_eval_set.scripts import SCRIPTS                         # noqa: E402


def main(argv):
    print()
    print(config.summary())
    print("data: %s" % config.data_root())

    args = [a for a in argv[1:] if not a.startswith("-")]
    flags = {a for a in argv[1:] if a.startswith("-")}

    # ---- show exactly what the model is told, then stop ----------------
    if "--prompt" in flags:
        from D2_tool_layer import prompt
        print()
        prompt.audit()
        return 0

    # ---- one named case, verbose --------------------------------------
    if args:
        case_id = args[0]
        print()
        print("-" * 68)
        print("  %s - every turn" % case_id)
        print("-" * 68)
        results, queue = run_set([case_id], verbose=True)
        if not results:
            return 1
        print()
        print("  DECISION RECORD")
        print(json.dumps(results[0]["record"], indent=2)[:2000])
        print()
        print("  CODE CHECK   %s" % ("PASS" if results[0]["passed"] else "FAIL"))
        for f in results[0]["fails"]:
            print("      %s" % f)
        print()
        print("  JUDGEMENT CHECK - not automated. Someone reads the reason")
        print("  and rules on each item:")
        for item in queue[0]["must_record"]:
            print("      [ ] %s" % item)
        print()
        return 0 if results[0]["passed"] else 1

    # ---- the set ------------------------------------------------------
    if "--all" in flags:
        cases = load_cases()
        print("\n  Running EVERY case in the work queue (%d)." % len(cases))
        print("  Cases with no script will stop the run - that is the")
        print("  scripted backend telling you to write one.")
    else:
        # Default: only what is scripted, so a clean clone always works.
        key = load_key()
        cases = [c for c in load_cases() if c in SCRIPTS and c in key]
        print("\n  Running the %d SCRIPTED case(s): %s"
              % (len(cases), ", ".join(cases)))
        print("  Add more to SCRIPTS in D4_eval_set/scripts.py, or use --all")
        print("  once you have scripted them.")

    if not cases:
        print("\n  Nothing to run for Problem %s." % config.PROBLEM)
        print("  config.PROBLEM is %r - is that the problem you chose?"
              % config.PROBLEM)
        return 1

    results, queue = run_set(cases)
    summary = report(results)

    # Beside this script, NOT in the working directory. Where the file
    # lands should not depend on which folder you happened to run from -
    # that is how a team ends up with three results.json in the tree and
    # quotes the wrong one in the report.
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "results.json")
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump({"config": config.summary(), "summary": summary,
                   "results": [{k: v for k, v in r.items()} for r in results],
                   "judgement_queue": queue}, fh, indent=2, default=str)
    print("  Wrote A2_main/results.json - COMMIT IT. Your result tables come")
    print("  from here, and a marker reads it alongside your report.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
