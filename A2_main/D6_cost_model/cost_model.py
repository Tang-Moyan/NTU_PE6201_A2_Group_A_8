"""
D6 - THE COST-TO-SERVE MODEL
=====================================================================
Working code: the three layers, the sensitivity range and the
break-even success rate. Pure functions, unit-tested in test_D6.py
against the brief's own worked figures.

THE THREE LAYERS (Class 5), and why they are separated:

  1 per-task variable    input + output tokens + tool fees.
                         LINEAR. Never amortises.
  2 per-task expected    (1 - success_rate) x cost of one failure.
    fallback             LINEAR. Never amortises. USUALLY THE LARGEST
                         LAYER, and the one almost every cost model
                         omits.
  3 fixed monthly        storage, infra, your eval runs, monitoring,
                         maintenance. Gets cheaper per task forever.

Layer 2 is where D4's pass rate lands. A cheap agent that is wrong
half the time is not cheap - which is why lever 4 of the ledger is the
success rate itself.

THE BASELINE RULE. Plain input and output tokens at list price.
Nothing cleverer. Prompt caching (pushes the bill DOWN) and reasoning
models (push it UP) are real, but they are model-specific and they
make a headline number impossible to check. Report the baseline first,
then the adjusted figure beside it if either applies.
=====================================================================
"""


# ---------------------------------------------------------------------
# layer 1 - per-task variable
# ---------------------------------------------------------------------
def layer1_variable(tokens_in, tokens_out, price_in_per_m, price_out_per_m,
                    tool_fees=0.0):
    """What one RUN costs in tokens, at list price."""
    return ((tokens_in / 1e6) * price_in_per_m
            + (tokens_out / 1e6) * price_out_per_m
            + tool_fees)


# ---------------------------------------------------------------------
# layer 2 - per-task expected fallback
# ---------------------------------------------------------------------
def failure_cost(hourly_rate, minutes_per_escalation):
    """Price a failure from LABOUR, not from a guess.

        failure_cost = hourly rate x minutes per escalation / 60

    A failure is not free just because no human is named in the design.
    Appendix A gives each problem a default role and handling time.
    """
    return float(hourly_rate) * float(minutes_per_escalation) / 60.0


def layer2_fallback(success_rate, one_failure_cost):
    """(1 - P) x failure_cost. The layer almost every model omits."""
    return (1.0 - float(success_rate)) * float(one_failure_cost)


# ---------------------------------------------------------------------
# layer 3 - fixed monthly
# ---------------------------------------------------------------------
def layer3_fixed(items):
    """Sum of {name: monthly_usd}. Gets cheaper per task forever."""
    return float(sum(items.values()))


# ---------------------------------------------------------------------
# putting them together
# ---------------------------------------------------------------------
def cost_per_task(variable, fallback):
    """Layers 1 + 2. What one ATTEMPT costs on average."""
    return variable + fallback


def cost_per_successful_task(variable, fallback, success_rate):
    """Class 5 escalation cost: layer 1 + layer 2.

    A failed outcome is escalated to a human; it is not retried until the
    model succeeds. Dividing by success_rate would apply the Class 4 retry
    formula and double-count failure handling here.
    """
    if not 0.0 < success_rate <= 1.0:
        raise ValueError("success_rate must be in (0, 1]; got %r" % success_rate)
    return variable + fallback


def monthly(variable, fallback, success_rate, fixed_monthly, tasks_per_month):
    """The figure a sponsor asks for: total, and per successful task."""
    per_attempt = cost_per_task(variable, fallback)
    total = per_attempt * tasks_per_month + fixed_monthly
    successes = tasks_per_month * success_rate
    return {
        "tasks_per_month": tasks_per_month,
        "layer1_total": variable * tasks_per_month,
        "layer2_total": fallback * tasks_per_month,
        "layer3_total": fixed_monthly,
        "total_usd": total,
        "successful_tasks": successes,
        "per_successful_task": (total / tasks_per_month)
        if tasks_per_month else None,
    }


# ---------------------------------------------------------------------
# the sensitivity range - not a point estimate
# ---------------------------------------------------------------------
def sensitivity(variable, one_failure_cost, success_rate, spread=0.10,
                steps=5):
    """Cost per successful task across success_rate +/- `spread`.

    Your success rate is an estimate and so is your failure cost. A
    robust answer and a knife-edge answer deserve different amounts of
    confidence, and a sponsor is entitled to know which one they are
    being handed.
    """
    lo = max(0.01, success_rate - spread)
    hi = min(1.0, success_rate + spread)
    rows = []
    for i in range(steps):
        p = lo + (hi - lo) * i / (steps - 1) if steps > 1 else success_rate
        fallback = layer2_fallback(p, one_failure_cost)
        rows.append((p, cost_per_successful_task(variable, fallback, p)))
    return rows


# ---------------------------------------------------------------------
# the break-even success rate - the question that decides what you ship
# ---------------------------------------------------------------------
def expensive_model_E(variable, success_rate, one_failure_cost):
    """The E that goes into break_even_success_rate().

    The brief defines it as "what one successful task costs on the
    expensive model - its tokens plus its own failures", and then says
    exactly which two things that is: LAYER 1 + LAYER 2 FOR THAT MODEL.

    Read that carefully, because the wording and the definition pull in
    different directions: "per successful task" sounds like it should
    be divided by the success rate, and the definition says it is not.
    We follow the definition, because that is what reproduces the
    brief's own worked answer of 91.2%. Dividing by P as well gives
    90.7% - close enough to look right and wrong enough to lose the
    mark, which is exactly the kind of thing to state in the report
    rather than leave implicit.
    """
    return variable + layer2_fallback(success_rate, one_failure_cost)


def break_even_success_rate(cheap_run_cost, expensive_cost_per_success,
                            one_failure_cost):
    """How good does the CHEAP model have to be to be worth choosing?

        break_even = 1 - (E - C) / F

    C  what one run costs on the cheap model - TOKENS ONLY
    E  what one SUCCESSFUL task costs on the expensive model, its own
       failures already folded in
    F  what one failure costs - the escalation

    WHY E INCLUDES ITS FAILURES AND C DOES NOT. For the expensive model
    you MEASURED its success rate, so you can price its failures. For
    the cheap model its success rate is the unknown you are solving
    for, so it cannot appear on that side of the sum. That asymmetry is
    the whole reason the formula looks lopsided.

    Returns a fraction, which may be negative (the cheap model wins
    however bad it is) or above 1 (it can never win).
    """
    C = float(cheap_run_cost)
    E = float(expensive_cost_per_success)
    F = float(one_failure_cost)
    if F <= 0:
        raise ValueError("failure cost must be positive; got %r" % F)
    return 1.0 - (E - C) / F


def break_even_verdict(break_even, measured_cheap_success_rate):
    """One sentence, which the brief says is the most useful thing in
    the report."""
    if measured_cheap_success_rate is None:
        return ("Not answerable yet: the cheap model has no measured success "
                "rate. Run D5(b).")
    gap = measured_cheap_success_rate - break_even
    if gap >= 0:
        return ("The cheap model clears its break-even: it needs %.1f%% and "
                "measured %.1f%%, %.1f points to spare."
                % (break_even * 100, measured_cheap_success_rate * 100,
                   gap * 100))
    return ("The cheap model falls short: it needs %.1f%% and measured "
            "%.1f%%, %.1f points short. When failures are expensive, the "
            "price of the model barely matters - accuracy does."
            % (break_even * 100, measured_cheap_success_rate * 100, -gap * 100))
