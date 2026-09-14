"""
D5 - THE MODEL BATTERY
=====================================================================
    python A2_main/D5_model_battery/battery.py               # scripted, free
    A2_LIVE=1 python A2_main/D5_model_battery/battery.py     # COSTS MONEY

TWO MODES, and the default is the free one on purpose.

  scripted   D5(a). Verifies a marker can clone the repository and
             reproduce your numbers with no key and no network. This
             is what caps Technical Execution if it does not work.

  live       D5(b). Runs the same evaluation set against each model in
             answers_D5.MODELS and reports where they diverge. Costs
             real money against a US$10 key, so it refuses to start
             without A2_LIVE=1 AND a key in the environment.

WHAT TO REPORT, and it is not "which model is best": which model does
YOUR JOB at what cost, and where they diverge. Expect the divergence
on the negative cases - that is the finding to look for, and it is why
this script reports the negative-only pass rate separately.

ON TOKEN COUNTS. The live backend in the scaffold returns zeros on
purpose. Wire in the usage numbers the API gives you before you run
the battery, or your D6 layer 1 will be an estimate wearing the label
"measured", which is the mistake D6 punishes. This script warns when
it sees a live run that reported zero tokens.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.template import is_filled                          # noqa: E402
from D4_eval_set import eval_runner                            # noqa: E402
from D5_model_battery import answers_D5 as A                   # noqa: E402

LIVE = os.environ.get("A2_LIVE") == "1"


# ---------------------------------------------------------------------
# D5(a) - the reproducible scripted run
# ---------------------------------------------------------------------
def scripted_default_in_file():
    """Read config.py as TEXT. What is committed is what a marker gets."""
    import re
    from common.bootstrap import code_file
    src = open(code_file("config.py"), encoding="utf-8").read()
    m = re.search(r'^BACKEND\s*=\s*"([^"]*)"', src, re.M)
    return (m.group(1) if m else None)


def scripted_run():
    """D5(a): the numbers a marker reproduces."""
    results, queue, unscripted = eval_runner.run()
    if not results:
        return None
    summary = eval_runner.summarise(results)
    summary["unscripted_cases"] = unscripted
    return summary


# ---------------------------------------------------------------------
# D5(b) - the live battery
# ---------------------------------------------------------------------
def live_models():
    return [m for m in A.MODELS if is_filled(m.get("slug"))]


def run_live_model(model):
    """Run the whole set against one model. Restores config afterwards."""
    import config
    saved = (config.BACKEND, config.MODEL, config.PRICE_IN, config.PRICE_OUT)
    try:
        config.BACKEND = "live"
        config.MODEL = model["slug"]
        if is_filled(model.get("price_in")):
            config.PRICE_IN = float(model["price_in"])
        if is_filled(model.get("price_out")):
            config.PRICE_OUT = float(model["price_out"])
        results, _queue, _unscripted = eval_runner.run(every=True)
        summary = eval_runner.summarise(results)
    finally:
        (config.BACKEND, config.MODEL,
         config.PRICE_IN, config.PRICE_OUT) = saved
    summary["model"] = model["slug"]
    summary["owner"] = model.get("owner")
    summary["tier"] = model.get("tier")
    return summary


def battery():
    if not LIVE:
        return None
    import config
    if not config.API_KEY:
        raise SystemExit(
            "\n  A2_LIVE=1 but OPENROUTER_API_KEY is not set.\n"
            "    export OPENROUTER_API_KEY='sk-or-...'\n"
            "  Each member runs one model on their own key - see\n"
            "  answers_D5.MODELS for who owns which.\n")
    models = live_models()
    if len(models) < 3:
        raise SystemExit(
            "\n  D5(b) needs at least three models; answers_D5.MODELS has "
            "%d filled in.\n" % len(models))
    return [run_live_model(m) for m in models]


# ---------------------------------------------------------------------
def report():
    import config
    fmt.h1("D5 - the model battery")

    # -- D5(a) --------------------------------------------------------
    fmt.h2("D5(a) - the scripted run a marker reproduces")
    committed = scripted_default_in_file()
    if committed == "scripted":
        fmt.ok('config.py commits BACKEND = "scripted"')
    else:
        fmt.fail('config.py commits BACKEND = %r' % committed)
        print("  A marker clones your repository and runs python run_eval.py.")
        print("  If your numbers do not come back, D5(a) has failed and")
        print("  Technical Execution is capped.")

    s = scripted_run()
    if s:
        fmt.kv("pass rate", "%.1f%%  (%d of %d trials, %d cases)"
               % (s["pass_rate"] * 100, s["passed"], s["trials"], s["cases"]))
        fmt.kv("median turns", s["median_turns"])
        fmt.kv("cost", "US$%.4f  (scripted - free)" % s["cost_usd"])
        if s["unscripted_cases"]:
            fmt.todo("%d labelled case(s) have no script yet"
                     % len(s["unscripted_cases"]))
    else:
        fmt.fail("the scripted run produced nothing")

    # -- D5(b) --------------------------------------------------------
    fmt.h2("D5(b) - the live battery")
    models = live_models()
    if not LIVE:
        print("  Not run. This is the default and it is deliberate: only")
        print("  D5(b) costs money. D3(b), D5(a) and D7 all run scripted.")
        print()
        fmt.kv("models declared", "%d of 3 minimum" % len(models))
        for m in A.MODELS:
            print("      %-28s owner: %s" % (m.get("slug"), m.get("owner")))
        print()
        print("  To run it:  set A2_LIVE=1 and OPENROUTER_API_KEY, then")
        print("      python A2_main/D5_model_battery/battery.py")
        print("  Split the models across the team - one member, one model,")
        print("  one key.")
        store.save("D5_battery", {"scripted": s, "live": None,
                                  "models_declared": len(models)},
                   source="D5/battery.py")
        return s

    rows = battery()
    fmt.table(["model", "tier", "owner", "pass rate", "negatives",
               "median turns", "cost US$"],
              [(r["model"], r.get("tier"), r.get("owner"),
                "%.1f%% (%d)" % (r["pass_rate"] * 100, r["trials"]),
                ("%.1f%% (%d)" % (r["negative_pass_rate"] * 100,
                                  r["negative_trials"]))
                if r["negative_pass_rate"] is not None else "-",
                r["median_turns"], "%.4f" % r["cost_usd"])
               for r in rows])

    zero = [r["model"] for r in rows if r["tokens_in"] == 0]
    if zero:
        fmt.fail("these models reported ZERO input tokens: %s" % ", ".join(zero))
        print("  The scaffold's live backend returns zeros on purpose. Wire")
        print("  in the usage block the API returns before you trust any of")
        print("  this - D6 needs MEASURED counts, and estimating while")
        print("  calling it measured is what D6 punishes.")

    fmt.h2("Where they diverged")
    fmt.paragraph(A.DIVERGENCE_FINDING)
    print()
    fmt.paragraph(A.WHICH_MODEL_WE_SHIP)

    store.save("D5_battery", {"scripted": s, "live": rows,
                              "models_declared": len(models)},
               source="D5/battery.py")
    return rows


if __name__ == "__main__":
    report()
    raise SystemExit(0)
