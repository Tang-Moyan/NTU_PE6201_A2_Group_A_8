"""
D1 - THE LOOP CONTRACT
=====================================================================
Working code. It does not build an agent - D1_agent_loop/agent.py is the
agent. What it does is CHECK that the loop you ship still satisfies
everything D1 requires, on a real run, every time you change it.

    from D1_agent_loop.loop_contract import verify
    report = verify("CLM-8842")

Eight clauses, each traceable to a sentence in the brief:

  1  one agent, one control loop        thought -> action -> observation
  2  it terminates                       every run reaches a final record
  3  several tools                       more than one distinct tool used
  4  MORE THAN ONE TOOL IN A TURN        the D2(c) requirement
  5  the loop is instrumented            turns, tokens, cost, evidence
  6  the gate sits in front of the       not in front of the agent
     irreversible step
  7  no framework owns the loop          no LangChain/LangGraph/CrewAI
  8  isolation                           the same case twice is identical

Clause 4 is the one teams get wrong by accident: a loop that CAN batch
calls but never does on your data has not met the requirement, and the
turn-count saving D2(c) claims will not be there.
=====================================================================
"""
import os
import re

FRAMEWORKS = ("langchain", "langgraph", "crewai", "autogen",
              "llama_index", "semantic_kernel", "haystack")


class ContractResult:
    """One clause: did it hold, and what did we see?"""

    def __init__(self, clause, held, detail):
        self.clause = clause
        self.held = held
        self.detail = detail

    def __repr__(self):
        return "<%s %s: %s>" % (self.clause, "held" if self.held else "BROKEN",
                                self.detail)


def verify(case_id, problem="A"):
    """Run one case and check every clause. Returns [ContractResult]."""
    import config
    from D1_agent_loop.agent import run_case

    record = run_case(case_id, problem=problem)
    out = []

    # 1 · one loop that produced a decision
    out.append(ContractResult(
        "1 one control loop",
        bool(record.get("decision")),
        "decision=%r" % record.get("decision")))

    # 2 · it terminated, and not by hitting the cap
    stopped = record.get("stopped_by")
    out.append(ContractResult(
        "2 terminates",
        record.get("turns", 0) > 0 and stopped != "step_cap",
        "turns=%s stopped_by=%r" % (record.get("turns"), stopped)))

    # 3 · several tools, not one
    evidence = record.get("evidence") or []
    distinct = sorted(set(evidence))
    out.append(ContractResult(
        "3 several tools",
        len(distinct) >= 3,
        "%d distinct: %s" % (len(distinct), ", ".join(distinct))))

    # 4 · MORE THAN ONE TOOL IN ONE TURN
    calls, turns = len(evidence), record.get("turns") or 0
    out.append(ContractResult(
        "4 multi-call turn",
        turns > 0 and calls > turns,
        "%d tool calls in %d turns - a loop that never batches has not "
        "met D2(c)" % (calls, turns)))

    # 5 · instrumented while the run happened
    needed = ("turns", "tokens_in", "tokens_out", "cost_usd", "evidence",
              "guardrails_fired", "backend")
    absent = [f for f in needed if f not in record]
    out.append(ContractResult(
        "5 instrumented",
        not absent,
        "missing: %s" % (", ".join(absent) or "nothing")))

    # 6 · the gate is in front of the ACTION, not the agent
    out.append(_gate_clause(record, problem))

    # 7 · no framework owns the loop
    out.append(_framework_clause())

    # 8 · isolation - the same case twice is the same record
    second = run_case(case_id, problem=problem)
    volatile = ("seconds",)
    a = {k: v for k, v in record.items() if k not in volatile}
    b = {k: v for k, v in second.items() if k not in volatile}
    out.append(ContractResult(
        "8 isolation",
        a == b,
        "two runs identical" if a == b else
        "runs differ on: %s" % sorted(k for k in a if a.get(k) != b.get(k))))

    return out


def _gate_clause(record, problem):
    from D2_tool_layer import tools
    gated = tools.GATED_ACTION.get(problem)
    fired = record.get("guardrails_fired") or []
    gate_events = [f for f in fired if str(f.get("guardrail", "")).startswith("gate")]
    evidence = record.get("evidence") or []

    if gated not in evidence and not gate_events:
        return ContractResult(
            "6 gate placement", True,
            "this run never reached %s, so the gate was correctly not "
            "consulted - an early exit is correct behaviour" % gated)
    if not gate_events:
        return ContractResult(
            "6 gate placement", False,
            "%s was called but no gate event was recorded" % gated)
    return ContractResult(
        "6 gate placement", True,
        "%s: %s" % (gated, gate_events[0].get("detail")))


def _framework_clause():
    """No library may own the loop. Ordinary libraries are fine."""
    from common.bootstrap import A2_MAIN
    hits = []
    for dirpath, dirnames, filenames in os.walk(A2_MAIN):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", "output", "data")]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            text = open(path, encoding="utf-8").read()
            for name in FRAMEWORKS:
                if re.search(r"^\s*(import|from)\s+%s\b" % name, text, re.M):
                    hits.append("%s imports %s"
                                % (os.path.relpath(path, A2_MAIN), name))
    return ContractResult(
        "7 hand-rolled loop",
        not hits,
        "; ".join(hits) if hits else
        "no agent framework imported - the loop is yours to be marked on")


def turn_shape(case_id, problem="A"):
    """How many calls landed in each turn, for the D1 write-up.

    Re-runs the case through the scripted backend and reads the script,
    because the decision record flattens `evidence` into one list and
    the SHAPE - which calls shared a turn - is the thing D2(c) is about.
    """
    from D4_eval_set import scripts
    script = scripts.SCRIPTS.get(case_id)
    if not script:
        return None
    shape = []
    for step in script:
        if "final" in step:
            continue
        shape.append([name for name, _ in step.get("calls", [])])
    return shape
