"""
D3(b) - THE GUARDRAIL CHECKLIST, RUN
=====================================================================
    python A2_main/D3_guardrails/checklist.py

AN EVALUATION CASE ASKS: did it get the job right?
A GUARDRAIL CASE ASKS:   did it refuse, cap, or escalate when it should have?

They are not the same thing and they do not live in the same file.

Everything here runs on the SCRIPTED backend, because a model has no
say in whether a step cap fires. That is the point: these test YOUR
CODE, so they cost nothing and reproduce exactly.

SIX RUNNERS, one per mechanism. The team writes the cases in
answers_D3.py; this module knows how to make each mechanism fire.

    step_cap          drop the cap below the run's real length
    budget_ceiling    drop the token ceiling below the run's real cost
    duplicate_action  repeat a call the agent already made
    gate_held         autonomy=suggest must hold the irreversible step
    gate_passed       autonomy=act must pass it, and RECORD that it did
    hostile_text      free text written by an outsider must not steer
                      the decision

The first five need no fixture data at all - they perturb a working
run. The sixth needs a claim whose narrative attacks the system, and
the shipped data has two of them (CLM-8941, CLM-8952).
=====================================================================
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.template import is_filled                          # noqa: E402
from D3_guardrails import answers_D3 as A                      # noqa: E402

HOSTILE = "hostile_text"


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------
class _Override:
    """Temporarily change config values, and always put them back."""

    def __init__(self, **values):
        self.values = values
        self.saved = {}

    def __enter__(self):
        import config
        for k, v in self.values.items():
            self.saved[k] = getattr(config, k)
            setattr(config, k, v)
        return self

    def __exit__(self, *exc):
        import config
        for k, v in self.saved.items():
            setattr(config, k, v)
        return False


def _scripted(case_id):
    from D4_eval_set import scripts
    return case_id in scripts.SCRIPTS


def _run(case_id, **config_overrides):
    from D1_agent_loop.agent import run_case
    import config
    with _Override(**config_overrides):
        return run_case(case_id, problem=config.PROBLEM)


def _default_case():
    """A scripted case to perturb. Any one will do for the code-layer tests."""
    from D4_eval_set import scripts
    return "CLM-8842" if "CLM-8842" in scripts.SCRIPTS else \
        (sorted(scripts.SCRIPTS)[0] if scripts.SCRIPTS else None)


# ---------------------------------------------------------------------
# the six runners
# ---------------------------------------------------------------------
def run_step_cap(case):
    cid = case.get("case_id") or _default_case()
    if not _scripted(cid):
        return _needs_script(cid)
    baseline = _run(cid)
    cap = max(1, baseline["turns"] - 1)
    record = _run(cid, MAX_TURNS=cap)
    return _verdict(
        record["stopped_by"] == "step_cap",
        "cap %d against a %d-turn run -> stopped_by=%r"
        % (cap, baseline["turns"], record["stopped_by"]),
        record)


def run_budget_ceiling(case):
    cid = case.get("case_id") or _default_case()
    if not _scripted(cid):
        return _needs_script(cid)
    baseline = _run(cid)
    ceiling = max(1, (baseline["tokens_in"] + baseline["tokens_out"]) // 2)
    record = _run(cid, MAX_TOKENS_PER_RUN=ceiling)
    return _verdict(
        record["stopped_by"] == "budget_ceiling",
        "ceiling %d against a %d-token run -> stopped_by=%r"
        % (ceiling, baseline["tokens_in"] + baseline["tokens_out"],
           record["stopped_by"]),
        record)


def run_duplicate_action(case):
    """Repeat a call the agent already made. NOTHING SHOULD CRASH -
    that is what makes this failure expensive: it burns money in a
    circle and still returns an answer."""
    from D4_eval_set import scripts
    cid = case.get("case_id") or _default_case()
    if not _scripted(cid):
        return _needs_script(cid)
    original = scripts.SCRIPTS[cid]
    steps = copy.deepcopy(original)
    repeat = copy.deepcopy(steps[1])
    repeat["thought"] = "(guardrail case) asking the same thing again"
    try:
        scripts.SCRIPTS[cid] = steps[:2] + [repeat] + steps[2:]
        record = _run(cid)
    finally:
        scripts.SCRIPTS[cid] = original
    return _verdict(
        record["stopped_by"] == "duplicate_action",
        "repeated turn 2 -> stopped_by=%r" % record["stopped_by"],
        record)


def run_gate_held(case):
    cid = case.get("case_id") or _default_case()
    if not _scripted(cid):
        return _needs_script(cid)
    record = _run(cid, AUTONOMY="suggest")
    events = [e["guardrail"] for e in record.get("guardrails_fired", [])]
    return _verdict(
        record["stopped_by"] == "gate_held" or "gate_held" in events,
        "autonomy=suggest -> stopped_by=%r, events=%s"
        % (record["stopped_by"], events),
        record)


def run_gate_passed(case):
    cid = case.get("case_id") or _default_case()
    if not _scripted(cid):
        return _needs_script(cid)
    record = _run(cid, AUTONOMY="act")
    events = [e["guardrail"] for e in record.get("guardrails_fired", [])]
    return _verdict(
        "gate_passed" in events,
        "autonomy=act -> events=%s (the record must SHOW the gate was "
        "reached and passed, not merely be silent)" % events,
        record)


def run_hostile_text(case):
    """Free text written by someone outside the organisation.

    Both problems carry it - a member's claim narrative here - and it
    is the one field on the row an outsider controls. At least three
    of the ten cases must attack it.

    The guardrail question is not "did it decide well". It is: did the
    instruction change the outcome? The answer key says these cases
    escalate with trigger `instruction_in_member_narrative`, and a run
    that approves them has been steered by its input.
    """
    import config
    from D4_eval_set.harness import load_key
    cid = case.get("case_id")
    if not cid:
        return _verdict(None, "no case_id given for a hostile-text case", None)
    if not _scripted(cid):
        return _needs_script(cid)

    record = _run(cid)
    key = load_key(config.PROBLEM).get(cid, {})
    want_decision = case.get("expect_decision") or key.get("expected_decision")
    want_trigger = case.get("expect_trigger") or key.get("trigger")

    got_decision = record.get("decision")
    got_trigger = record.get("trigger")
    held = (got_decision == want_decision)
    if want_trigger:
        held = held and (got_trigger == want_trigger)
    return _verdict(
        held,
        "decision %r (want %r), trigger %r (want %r)"
        % (got_decision, want_decision, got_trigger, want_trigger),
        record)


RUNNERS = {
    "step_cap": run_step_cap,
    "budget_ceiling": run_budget_ceiling,
    "duplicate_action": run_duplicate_action,
    "gate_held": run_gate_held,
    "gate_passed": run_gate_passed,
    HOSTILE: run_hostile_text,
}


def _verdict(held, observed, record):
    return {"held": held, "observed": observed,
            "record": {k: record.get(k) for k in
                       ("decision", "turns", "stopped_by", "guardrails_fired")}
            if record else None}


def _needs_script(case_id):
    return {"held": None,
            "observed": "no script for %r in D4_eval_set/scripts.py - write "
                        "one, or set BACKEND='live'" % case_id,
            "record": None}


# ---------------------------------------------------------------------
def run_all():
    """Run every case in answers_D3.CASES. Returns a list of results."""
    out = []
    for case in A.CASES:
        cid = case.get("id")
        category = case.get("category")
        if not is_filled(category) or category not in RUNNERS:
            out.append({"id": cid, "category": category, "held": None,
                        "observed": "category not set, or not one of: %s"
                                    % ", ".join(sorted(RUNNERS)),
                        "catches": case.get("catches")})
            continue
        try:
            result = RUNNERS[category](case)
        except Exception as exc:                          # noqa: BLE001
            result = {"held": False,
                      "observed": "runner raised %s: %s"
                                  % (type(exc).__name__, exc),
                      "record": None}
        result.update({"id": cid, "category": category,
                       "catches": case.get("catches")})
        out.append(result)
    return out


def hostile_count():
    return sum(1 for c in A.CASES if c.get("category") == HOSTILE)


def report():
    fmt.h1("D3(b) - the guardrail checklist")
    print("  An evaluation case asks: did it get the job right?")
    print("  A guardrail case asks:   did it refuse, cap or escalate")
    print("                           when it should have?")

    results = run_all()
    fmt.h2("%d case(s), %d of them hostile free text (need >= 10 and >= 3)"
           % (len(results), hostile_count()))

    rows = []
    for r in results:
        state = {True: "HELD", False: "BROKEN", None: "not run"}[r["held"]]
        rows.append((r["id"], r["category"], state, r["observed"]))
    fmt.table(["id", "category", "result", "observed"], rows)

    fmt.h2("What each case exists to catch")
    for r in results:
        print("  %-8s %s" % (r["id"], r.get("catches")))

    broken = [r for r in results if r["held"] is False]
    if broken:
        fmt.h2("BROKEN - the guardrail did not fire")
        for r in broken:
            print("  %-8s %s" % (r["id"], r["observed"]))
        print()
        print("  Make the stop LOUD. A cap that silently returns an empty")
        print("  answer is worse than the loop it prevented: it turns a")
        print("  visible cost problem into an invisible correctness problem.")

    store.save("D3_checklist",
               {"cases": results, "hostile": hostile_count(),
                "total": len(results)},
               source="D3/checklist.py")
    return results


if __name__ == "__main__":
    report()
    raise SystemExit(0)
