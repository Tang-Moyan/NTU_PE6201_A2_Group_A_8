"""
D6 - THE FULL COST REPORT
=====================================================================
    python A2_main/D6_cost_model/levers.py

Assembles report section 4 from answers_D6.py plus the measurements
D2, D4 and D5 already wrote into output/. Where a lever was measured
by another deliverable, this pulls the real number rather than asking
you to re-type it - so the ledger cannot disagree with the experiment
that produced it.

Prints, in the order the brief asks for them:

    the three layers, separated
    cost per successful task
    the monthly figure at your volume
    the sensitivity range (+/- 10 points)
    the break-even success rate, and the one-sentence verdict
    the four-lever ledger, with measured before and after
    the three caps
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.template import is_filled                          # noqa: E402
from D6_cost_model import answers_D6 as A                      # noqa: E402
from D6_cost_model import cost_model                           # noqa: E402


def measured_inputs():
    """Everything D6 needs that another deliverable already measured."""
    evaluation = store.load("D4_eval") or {}
    parallel = store.load("D2_parallel") or {}
    audit = store.load("D2_tool_audit") or {}
    descriptor = store.load("D2_descriptor") or {}
    battery = store.load("D5_battery") or {}
    return {"eval": evaluation, "parallel": parallel, "audit": audit,
            "descriptor": descriptor, "battery": battery}


def _live_rows(battery):
    """Read live measurements from the merged file or owner shards."""
    rows = list((battery or {}).get("live") or [])
    if rows:
        return rows
    for owner in ("Jojo", "Moyan", "Keerthi", "Xianer", "Ziyu", "Lufei"):
        shard = store.load("D5_battery_%s" % owner) or {}
        rows.extend(shard.get("live") or [])
    return rows


def baseline():
    """Layers 1 and 2 for one run, from measured tokens and pass rate."""
    m = measured_inputs()
    evaluation = next((r for r in _live_rows(m["battery"])
                       if r.get("model") == A.EXPENSIVE_MODEL), None)
    if not evaluation or not evaluation.get("trials"):
        return None
    if not (is_filled(A.PRICE_IN_PER_M) and is_filled(A.PRICE_OUT_PER_M)):
        return None

    trials = evaluation["trials"]
    tin = evaluation["tokens_in"] / trials
    tout = evaluation["tokens_out"] / trials
    variable = cost_model.layer1_variable(
        tin, tout, float(A.PRICE_IN_PER_M), float(A.PRICE_OUT_PER_M))

    if not (is_filled(A.HOURLY_RATE_USD) and is_filled(A.MINUTES_PER_ESCALATION)):
        return {"variable": variable, "tokens_in": tin, "tokens_out": tout,
                "success_rate": evaluation["pass_rate"], "failure_cost": None}

    f = cost_model.failure_cost(A.HOURLY_RATE_USD, A.MINUTES_PER_ESCALATION)
    p = evaluation["pass_rate"]
    return {"variable": variable,
            "tokens_in": tin, "tokens_out": tout,
            "success_rate": p,
            "failure_cost": f,
            "fallback": cost_model.layer2_fallback(p, f),
            "estimated_tokens": False}


def report():
    fmt.h1("D6 - the cost-to-serve model")
    m = measured_inputs()

    b = baseline()
    if b is None:
        fmt.fail("not enough measured input yet")
        print("  D6 needs, in this order:")
        print("    1. python A2_main/D4_eval_set/eval_runner.py   (pass rate,")
        print("       token counts)")
        print("    2. PRICE_IN_PER_M / PRICE_OUT_PER_M in answers_D6.py")
        print("    3. HOURLY_RATE_USD / MINUTES_PER_ESCALATION for layer 2")
        return None

    # -- the three layers ---------------------------------------------
    fmt.h2("The three layers, separated")
    print("  Baseline: plain input and output tokens at list price. Nothing")
    print("  cleverer - caching and reasoning models are reported beside it,")
    print("  never inside it.")
    print()
    fmt.kv("tokens per run", "%.0f in / %.0f out" % (b["tokens_in"], b["tokens_out"]))
    fmt.kv("1 · per-task variable", "US$%.5f  (linear, never amortises)"
           % b["variable"])
    if b.get("failure_cost") is None:
        fmt.todo("2 · per-task fallback not priced",
                 "fill HOURLY_RATE_USD and MINUTES_PER_ESCALATION")
        return None
    fmt.kv("   one failure costs", "US$%.2f  (%s, %s min at US$%s/hr)"
           % (b["failure_cost"], A.ESCALATION_ROLE, A.MINUTES_PER_ESCALATION,
              A.HOURLY_RATE_USD))
    fmt.kv("2 · per-task fallback",
           "US$%.5f  = (1 - %.3f) x US$%.2f"
           % (b["fallback"], b["success_rate"], b["failure_cost"]))

    fixed = cost_model.layer3_fixed(A.FIXED_MONTHLY) if is_filled(A.FIXED_MONTHLY) else None
    if fixed is None:
        fmt.todo("3 · fixed monthly not filled in")
    else:
        fmt.kv("3 · fixed monthly", "US$%.2f  (gets cheaper per task forever)"
               % fixed)

    ratio = b["fallback"] / b["variable"] if b["variable"] else 0
    print()
    print("  Layer 2 is %.1fx layer 1 here. It is usually the largest layer,"
          % ratio)
    print("  and it is the one almost every cost model omits.")
    if b.get("estimated_tokens"):
        print()
        print("  NOTE: these token counts came from the SCRIPTED backend and")
        print("  are estimates. D6 wants MEASURED counts - take them from the")
        print("  usage block the API returns on the D5 live battery before")
        print("  you put this number in the report.")

    cps = cost_model.cost_per_successful_task(
        b["variable"], b["fallback"], b["success_rate"])
    fmt.kv("cost per SUCCESSFUL task", "US$%.5f" % cps)

    # -- monthly -------------------------------------------------------
    if fixed is not None and is_filled(A.TASKS_PER_MONTH):
        fmt.h2("At your volume")
        mo = cost_model.monthly(b["variable"], b["fallback"], b["success_rate"],
                                fixed, int(A.TASKS_PER_MONTH))
        fmt.table(["", "US$ / month"],
                  [("layer 1 · variable", "%.2f" % mo["layer1_total"]),
                   ("layer 2 · fallback", "%.2f" % mo["layer2_total"]),
                   ("layer 3 · fixed", "%.2f" % mo["layer3_total"]),
                   ("TOTAL", "%.2f" % mo["total_usd"]),
                   ("per successful task", "%.5f" % mo["per_successful_task"])],
                  aligns=["<", ">"])
    else:
        mo = None
        fmt.todo("monthly figure needs FIXED_MONTHLY and TASKS_PER_MONTH")

    # -- sensitivity ----------------------------------------------------
    fmt.h2("Sensitivity - a range, not a point estimate")
    rows = cost_model.sensitivity(b["variable"], b["failure_cost"],
                                  b["success_rate"])
    fmt.table(["success rate", "cost per successful task US$"],
              [("%.1f%%" % (p * 100), "%.5f" % c) for p, c in rows],
              aligns=[">", ">"])
    spread = rows[-1][1] - rows[0][1]
    print()
    print("  Across +/- 10 points the cost per success moves by US$%.5f"
          % abs(spread))
    print("  (%.0f%% of the midpoint). Say whether your conclusion survives"
          % (abs(spread) / rows[len(rows) // 2][1] * 100))
    print("  the whole range - a robust answer and a knife-edge answer")
    print("  deserve different amounts of confidence.")

    # -- break-even -----------------------------------------------------
    fmt.h2("Break-even - the question that decides which model you ship")
    be = _break_even(b)
    if be is None:
        fmt.todo("needs CHEAP_MODEL / EXPENSIVE_MODEL and their measured "
                 "success rates from the D5 live battery")
    else:
        fmt.kv("C  cheap model, one run (tokens only)", "US$%.5f" % be["C"])
        fmt.kv("E  expensive model, one SUCCESS", "US$%.5f" % be["E"])
        fmt.kv("F  one failure", "US$%.2f" % be["F"])
        print()
        fmt.kv("break-even success rate", "%.1f%%" % (be["break_even"] * 100))
        print()
        fmt.paragraph(be["verdict"])
        print()
        print("  Why E includes its failures and C does not: for the expensive")
        print("  model you MEASURED the success rate, so you can price its")
        print("  failures. For the cheap model that rate is the unknown you")
        print("  are solving for, so it cannot appear on that side of the sum.")
    fmt.paragraph(A.BREAK_EVEN_READING)

    # -- the ledger ------------------------------------------------------
    fmt.h2("The cost ledger - four levers, measured before and after")
    _ledger(m)

    fmt.h2("The three caps that ship with it")
    for name, value in A.CAPS.items():
        fmt.kv(name, value)

    # -- the two adjustments ---------------------------------------------
    fmt.h2("Adjustments reported BESIDE the baseline, never inside it")
    print("  prompt caching (pushes the bill DOWN):")
    fmt.paragraph(A.CACHING_MEASURED, indent=4)
    print("  reasoning model (pushes the bill UP):")
    fmt.paragraph(A.REASONING_MODEL_MEASURED, indent=4)

    payload = {"baseline": b, "monthly": mo, "sensitivity": rows,
               "break_even": be, "cost_per_successful_task": cps}
    store.save("D6_cost", payload, source="D6/levers.py")
    return payload


def _break_even(b):
    if not (is_filled(A.CHEAP_MEASURED_SUCCESS_RATE)
            and is_filled(A.EXPENSIVE_MEASURED_SUCCESS_RATE)):
        return None
    if A.CHEAP_MEASURED_SUCCESS_RATE is None or \
            A.EXPENSIVE_MEASURED_SUCCESS_RATE is None:
        return None

    live = _live_rows(store.load("D5_battery") or {})
    by_slug = {r["model"]: r for r in live}
    cheap = by_slug.get(A.CHEAP_MODEL)
    expensive = by_slug.get(A.EXPENSIVE_MODEL)
    if not (cheap and expensive):
        return None

    F = b["failure_cost"]
    C = cheap["cost_usd"] / max(1, cheap["trials"])
    e_variable = expensive["cost_usd"] / max(1, expensive["trials"])
    e_p = float(expensive["pass_rate"])
    E = cost_model.expensive_model_E(e_variable, e_p, F)
    be = cost_model.break_even_success_rate(C, E, F)
    return {"C": C, "E": E, "F": F, "break_even": be,
            "verdict": cost_model.break_even_verdict(
                be, float(cheap["pass_rate"]))}


def _ledger(m):
    """Pull each lever's measured numbers from the deliverable that owns it."""
    auto = {}
    audit = m["audit"].get("sizes") or {}
    if audit:
        auto[1] = "now ~%d tokens of tool definitions (%d tools)" % (
            audit.get("tool_block_tokens", 0), len(audit.get("per_tool", {})))
    par = m["parallel"]
    if par:
        auto[2] = ("sequential %d turns / %d input tokens  ->  parallel %d / %d"
                   % (par["sequential"]["total_turns"],
                      par["sequential"]["tokens_in"],
                      par["parallel"]["total_turns"],
                      par["parallel"]["tokens_in"]))
    desc = (m["descriptor"] or {}).get("returns") or {}
    if desc.get("v2_avg_tokens") is not None:
        auto[3] = "v2 returns ~%.0f tokens per call%s" % (
            desc["v2_avg_tokens"],
            (", v1 ~%.0f" % desc["v1_avg_tokens"])
            if desc.get("v1_avg_tokens") is not None else " (v1 not written)")
    ev = next((r for r in _live_rows(m["battery"])
               if r.get("model") == A.EXPENSIVE_MODEL), None)
    if ev:
        auto[4] = "measured %.1f%% over %d trial(s)" % (
            ev["pass_rate"] * 100, ev["trials"])

    rows = []
    for n in (1, 2, 3, 4):
        lever = A.LEVERS[n]
        rows.append((n, lever["what"], lever["built_in"],
                     auto.get(n, "not measured yet")))
    fmt.table(["#", "what it attacks", "built in", "measured"], rows,
              aligns=[">", "<", "<", "<"])
    print()
    for n in (1, 2, 3, 4):
        lever = A.LEVERS[n]
        print("  lever %d  before: %s" % (n, lever["before"]))
        print("           after : %s" % lever["after"])
        print("           note  : %s" % lever["note"])
    print()
    print("  Levers 1 and 3 look similar and are not: a fat tool block is")
    print("  LINEAR in turns, a fat observation COMPOUNDS. Both are worth")
    print("  cutting; only one of them explodes.")
    fmt.paragraph(A.DOMINANT_LEVER)


if __name__ == "__main__":
    report()
    raise SystemExit(0)
