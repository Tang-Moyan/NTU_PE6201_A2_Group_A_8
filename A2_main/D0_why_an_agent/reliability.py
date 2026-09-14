"""
D0(b) Test 2 - THE ARITHMETIC
=====================================================================
Working code. Nothing here is a template; the numbers it eats come
from D4 (pass rate) and D7 (median turns), and it is the same argument
measured three times:

    run success   P = s ** T
    implied step  s = P ** (1/T)

You cannot measure per-step reliability directly. What D4 measures is
whether a WHOLE RUN produced the right outcome. So you work backwards:
given a measured run pass rate P over a measured median turn count T,
s is the per-step reliability that would produce it.

WHY THIS MATTERS BEYOND D0. The same s at a different T gives a very
different P - which is why D2(c)'s parallel calling (fewer turns) and
D6's layer 2 ((1-P) x failure_cost) are not three separate exercises.
Cut T and P rises with no change in step quality at all.

TREAT s AS A DIAGNOSTIC, NOT A CONSTANT. Steps are not independent - a
bad observation early makes later steps worse - and they are not
equally failure-prone: the turn that reads a policy row is near
perfect, the turn that judges a member's narrative is not. A single
number averages them and hides which is which. The question s answers
is only: "is my problem step QUALITY or step COUNT?"
=====================================================================
"""


def run_success(step_reliability, turns):
    """P = s ** T. What a run is worth when every step must hold."""
    return float(step_reliability) ** float(turns)


def implied_step_reliability(pass_rate, turns):
    """s = P ** (1/T). The backwards direction, and the one you use."""
    pass_rate = float(pass_rate)
    turns = float(turns)
    if not 0.0 < pass_rate <= 1.0:
        raise ValueError("pass_rate must be in (0, 1]; got %r" % pass_rate)
    if turns <= 0:
        raise ValueError("turns must be positive; got %r" % turns)
    return pass_rate ** (1.0 / turns)


def turn_sensitivity(step_reliability, turn_counts):
    """[(T, P), ...] - the same step quality at different turn counts.

    This is the table that makes Way 2 (cut the number of steps) the
    biggest win: hold s fixed, vary T, and watch P move on its own.
    """
    return [(t, run_success(step_reliability, t)) for t in turn_counts]


def turns_for_target(step_reliability, target_pass_rate):
    """The largest T that still clears `target_pass_rate` at this s.

    Answers "how many turns can I afford?" rather than "what do I get?".
    Returns None when even a single turn falls short.
    """
    import math
    s = float(step_reliability)
    target = float(target_pass_rate)
    if not 0.0 < s < 1.0:
        raise ValueError("step_reliability must be in (0, 1); got %r" % s)
    if not 0.0 < target <= 1.0:
        raise ValueError("target must be in (0, 1]; got %r" % target)
    t = math.floor(math.log(target) / math.log(s))
    return t if t >= 1 else None


def weak_step_candidates(results):
    """Group failing runs by the tool call that came immediately before.

    THE POINT OF THE EXERCISE. Not every step has the same s, and the
    turn that shows up most often just before a wrong outcome is your
    candidate for the weak one. Your trace log already holds this - the
    scaffold records `evidence`, an ordered list of every tool called.

    `results` is the list produced by harness.run_set(): each row has
    `passed` and `record["evidence"]`.

    Returns [(tool_name, failures, appearances, failure_share), ...],
    worst first. `failure_share` is failures / appearances, so a tool
    that is called on every run does not top the table merely for being
    popular.
    """
    failures, appearances = {}, {}
    for row in results:
        evidence = (row.get("record") or {}).get("evidence") or []
        for name in set(evidence):
            appearances[name] = appearances.get(name, 0) + 1
        if row.get("passed"):
            continue
        # The LAST tool called before the run concluded is the one that
        # was in front of the agent when it went wrong.
        if evidence:
            last = evidence[-1]
            failures[last] = failures.get(last, 0) + 1

    rows = []
    for name, appeared in appearances.items():
        failed = failures.get(name, 0)
        rows.append((name, failed, appeared,
                     (failed / appeared) if appeared else 0.0))
    rows.sort(key=lambda r: (-r[3], -r[1], r[0]))
    return rows


def two_moves(weak_step):
    """The two levers a weak step gives you. They are NOT the same lever.

    Returned as data so the report and the test script quote the same
    words. See D0 WORKPLAN for how to choose between them.
    """
    return [
        {"move": "(a) fix the step",
         "how": "a better tool descriptor, a filtered return, a tighter type",
         "class4_way": "Way 1 - raise per-step reliability",
         "changes": "s goes up, so P goes up",
         "built_in": "D2(b)",
         "applied_to": weak_step},
        {"move": "(b) remove or bypass the step",
         "how": "cut the tool, move the work into ordinary code, or fold it "
                "into a parallel turn",
         "class4_way": "Way 2 - cut the number of steps",
         "changes": "T goes down, so P goes up",
         "built_in": "D2(a) and D2(c)",
         "applied_to": weak_step},
    ]


def summarise(pass_rate, median_turns, comparison_turns=(4, 8, 12, 16, 20)):
    """Everything D0(b) Test 2 asks for, as one dict.

    Kept separate from printing so the report assembler and the test
    script cannot disagree about the numbers.
    """
    s = implied_step_reliability(pass_rate, median_turns)
    return {
        "measured_pass_rate": pass_rate,
        "measured_median_turns": median_turns,
        "implied_step_reliability": s,
        "turn_sensitivity": turn_sensitivity(s, comparison_turns),
        "turns_for_90pc": turns_for_target(s, 0.90) if s < 1.0 else None,
    }
