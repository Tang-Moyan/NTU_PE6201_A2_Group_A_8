"""
D2 - USER WORK FILE  ("The tool layer")
=====================================================================
Report section 2 has a 450-word budget, the largest of the six sections.
Conceptual Understanding and Reasoning & Justification together are 50%
of the mark; a large share of that lands here.

Three parts:
  D2(a)  The tool set is chosen, not accumulated
  D2(b)  Tool descriptors + at least two poka-yoke + one measured rewrite
  D2(c)  A dependency rule for multi-call turns + a measured saving

Self-check:  python A2_main/D2_tool_layer/test_D2.py
=====================================================================
"""
from common.template import TEMPLATE

# =====================================================================
# D2(a) - Tool set: score every tool on three questions
# =====================================================================
# Every tool in REGISTRY needs a row; test_D2.py checks that none are missing.
# Three questions:
#   1 Without it, which task actually fails? Name the task. Start from the
#     minimum set; add only for observed failures, never imagined ones.
#   2 Will the model confuse it with a neighbour? The driver is
#     distinguishability, not count. Ten clearly different tools are fine;
#     three overlapping ones are trouble. If you cannot say in one sentence
#     when to use A rather than B, the model cannot either.
#   3 What does it cost when it is never called? It lives in the prompt
#     prefix, is re-sent and re-billed every turn, enlarges the failure
#     surface you cannot exhaustively test, and if it writes, it needs a
#     gate.

TOOL_AUDIT = {
    "get_claim": {
        "fails_without_it": (
            "No other tool turns a claim id into the member, hospital, date, "
            "documents, and line items needed by the later checks."
        ),
        "confusable_with": (
            "No. get_claim retrieves the case itself; the other tools check "
            "one part of that case."
        ),
        "cost_when_never_called": (
            "It is the entry tool, so a normal claim run needs it. Its "
            "descriptor still adds prompt cost on every turn."
        ),
        "verdict": "keep",
    },
    "lookup_policy": {
        "fails_without_it": (
            "The agent cannot check policy status, policy dates, remaining "
            "annual limit, or policy exclusions."
        ),
        "confusable_with": (
            "No. lookup_policy gives whole-policy facts; check_coverage gives "
            "the result for one procedure line."
        ),
        "cost_when_never_called": (
            "Its descriptor adds prompt cost even if a run ends before using "
            "it, but policy status and remaining limit are needed for policy "
            "escalation cases."
        ),
        "verdict": "keep",
    },
    "check_coverage": {
        "fails_without_it": (
            "The agent cannot tell whether each procedure is covered, "
            "excluded, needs pre-authorisation, or needs a document."
        ),
        "confusable_with": (
            "No. It checks one procedure line; lookup_policy checks the "
            "member's full policy."
        ),
        "cost_when_never_called": (
            "It is called once for each line on ordinary claims. Its "
            "descriptor adds prompt cost even on early policy escalations "
            "where line checks are skipped."
        ),
        "verdict": "keep",
    },
    "get_preauthorisation": {
        "fails_without_it": (
            "The agent cannot tell whether a procedure needing "
            "pre-authorisation has a valid approval for the treatment date."
        ),
        "confusable_with": (
            "No. check_coverage says whether pre-authorisation is needed; "
            "get_preauthorisation checks whether it exists and is valid."
        ),
        "cost_when_never_called": (
            "Its descriptor adds prompt cost on claims with no "
            "pre-authorisation requirement, but it is only called after "
            "check_coverage says it is needed."
        ),
        "verdict": "keep",
    },
    "check_duplicate_claim": {
        "fails_without_it": (
            "The agent cannot detect a resubmitted claim. CLM-8933 must be "
            "escalated because it matches prior claim CLM-8710."
        ),
        "confusable_with": (
            "No. It compares the current claim with decided-claim history; "
            "no other tool reads that history."
        ),
        "cost_when_never_called": (
            "Its descriptor adds prompt cost even when no duplicate is found, "
            "but the tool covers the distinct duplicate-claim failure mode."
        ),
        "verdict": "keep",
    },
    "issue_decision_letter": {
        "fails_without_it": (
            "The whole task has no final decision output without it."
        ),
        "confusable_with": (
            "No. It is the only tool that writes a decision; all other tools "
            "only return information."
        ),
        "cost_when_never_called": (
            "It is irreversible, so it needs a gate; this is already covered "
            "by the autonomy setting."
        ),
        "verdict": "keep",
    },
}

# Tools we cut — this is explicit extra credit.
# "A tool you removed, naming the observation that removed it, earns
#  explicit credit - that is the behaviour nobody does naturally."
# Each item: {"tool", "why_added", "observation_that_removed_it"}
# If you cut none, use []. First ask: of your seven tools, which most
# resembles Class 4's search_notes (fails both question 1 and question 2)?
TOOLS_CUT = [
    {
        "tool": "lookup_hospital",
        "why_added": (
            "It was part of the scaffold's seven-tool starting interface so "
            "the agent could retrieve a hospital's name and panel status."
        ),
        "observation_that_removed_it": (
            "CLM-8874 uses H-330 (Bayfront Specialist), which is non-panel, "
            "but its expected decision is still approve_in_principle. It "
            "changes what the record must SAY, not what the decision is. We "
            "changed get_claim to return the hospital details on its first "
            "call and removed the separate lookup_hospital call. CLM-8842 "
            "still passed after the change: approve_in_principle in four "
            "turns, with seven tool calls instead of eight."
        ),
    }
]

# Before adding a tool, try not adding one. Four moves, in priority order —
# the report should say which of them you tried.
FOUR_MOVES_TRIED = {
    1: (
        "Considered, but no change was needed. check_coverage already "
        "receives the procedure code, and required_documents.json is keyed "
        "by that code. We did not need to add another input argument."
    ),
    2: (
        "Used. Before the change, no tool read required_documents.json. We "
        "changed check_coverage to return required_document for the procedure "
        "code it already receives. On CLM-8901, the claim had no documents "
        "and procedure 45378 returned required_document: itemised_bill. A "
        "procedure with no requirement (70553) returned required_document: "
        "None. We also used this move earlier by returning hospital details "
        "from get_claim and removing lookup_hospital."
    ),
    3: (
        "Not used. We kept the required-document result inside "
        "check_coverage rather than moving it into separate ordinary code."
    ),
    4: (
        "Not used. We did not add a new required-document tool because "
        "check_coverage now returns the needed information."
    ),
}

SHORTEST_DEFENSIBLE_LIST = (
    "Five read-only tools provide the claim and hospital details, policy "
    "status and limits, per-line coverage and document requirements, "
    "pre-authorisation status, and duplicate history; one gated irreversible "
    "tool writes the final decision. lookup_hospital was removed because its "
    "record-only facts now come from get_claim."
)


# =====================================================================
# D2(b) - Descriptors, poka-yoke, and one measured rewrite
# =====================================================================

# ---------------------------------------------------------------------
# At least two poka-yoke. The key requirement: say what it makes
# impossible, not what it "discourages".
# One already in the scaffold: check_coverage requires policy_id, so you
# cannot look up coverage against "no policy".
# ---------------------------------------------------------------------
POKA_YOKE = [
    {"before": TEMPLATE("Signature / shape before the change",
                        example="check_coverage(code)"),
     "after": TEMPLATE("After the change",
                       example="check_coverage(code, policy_id)"),
     "makes_impossible": TEMPLATE(
         "What does it make impossible? Must be impossible, not discouraged.",
         example="Checking coverage against no policy at all and getting a "
                 "confident answer about nothing.")},
    {"before": TEMPLATE("Before the change"),
     "after": TEMPLATE("After the change"),
     "makes_impossible": TEMPLATE("What does it make impossible?")},
]

# ---------------------------------------------------------------------
# One measured rewrite. Pick one tool, write v1 and v2 descriptors plus
# return shapes, and report three numbers: tokens returned per call,
# evaluation pass rate, guardrail cases passed.
#
# Important: v2 should be the version now in D2_tool_layer/tools.py::DESCRIPTORS
# (the good one). v1 is the version you deliberately made worse — the
# experiment's control.
#
# Honesty requirement: if v2 is neither smaller nor safer, say so.
# "a rewrite that did not help, honestly reported, scores better than
#  one that was never measured."
# ---------------------------------------------------------------------
DESCRIPTOR_EXPERIMENT_TOOL = TEMPLATE(
    "Which tool is this experiment on? Suggested: get_preauthorisation — "
    "its failure field carries the costliest misread in the assignment "
    "(None is not the same as not covered).",
    example="get_preauthorisation")

# v1: a deliberately worse six-field descriptor. You decide how it is
# worse; a common choice is to degrade the failure field to "returns null"
# (exactly the mistake Class 4 says teams make most often).
DESCRIPTOR_V1 = {
    "name": TEMPLATE("Tool name, same as v2", example="get_preauthorisation"),
    "purpose": TEMPLATE("v1 purpose", example="Look up a pre-authorisation."),
    "when": TEMPLATE("v1 when", example="When you need one."),
    "args": TEMPLATE("v1 args, as a dict",
                     example={"member_id": "str", "procedure_code": "str",
                              "date_of_service": "str"}),
    "returns": TEMPLATE("v1 returns", example="the pre-authorisation or null"),
    "failure": TEMPLATE(
        "v1 failure. This is the core of the experiment: degrading it to "
        "'Returns null.' is already bad enough.",
        example="Returns null."),
}


def v1_return(tool_name, args, result):
    """v1 return shape: degrade v2's return into a fatter / more raw version.

    This is the **code** you write for D2(b) (not a fill-in). The framework
    calls it to measure "tokens returned per call, v1 vs v2".

    Typical pattern: v2 returns a filtered projection; v1 returns the whole
    raw row. For example:

        def v1_return(tool_name, args, result):
            if tool_name != "get_preauthorisation" or result is None:
                return result
            # v1 dumps the matching row from the preauthorisations table
            # as-is, plus a pile of unrelated fields, and lets the model
            # filter
            from D2_tool_layer import tools
            rows = tools._load("A", "preauthorisations")
            return {"query": args, "all_rows": rows, "match": result}

    Returning `result` itself means "this tool is unchanged in v1".
    When you have written it, delete the raise below.
    """
    raise NotImplementedError(
        "D2(b): write v1_return() in answers_D2.py. See the docstring above. "
        "Until then the framework can compare descriptors but not return "
        "shapes, and D2(b) asks for both.")


DESCRIPTOR_EXPERIMENT_VERDICT = TEMPLATE(
    "Verdict after seeing the three numbers. Is v2 smaller? Safer? If "
    "neither, say so — an honestly reported rewrite that did not help "
    "scores higher than one that was never measured. Also answer the Class 4 "
    "Section 7 point: a prompt instruction is paid on every call, every run, "
    "forever, and dies when you change models; an interface constraint is "
    "paid once and holds permanently.",
    example="v2's descriptor is 180 tokens longer and its return is 60% "
            "smaller. The descriptor cost is paid once per turn; the return "
            "cost compounds, because every observation is re-sent on every "
            "later turn. Net saving on our median run: ...")


# =====================================================================
# D2(c) - Multi-call turns: dependency rule and measurement
# =====================================================================

# Dependency rule: which tools may share a turn, and which may not.
# There is only one criterion: a pair may run in parallel if and only if
# neither needs the other's output.
#
# Ready-made structure for Problem A:
#   turn 1  get_claim                        must run alone — everything
#                                            later needs its return
#   turn 2  lookup_policy + check_coverage×n
#                                            mutually independent
#   turn 3  get_preauthorisation             cannot join turn 2 —
#                                            until coverage answers, you
#                                            do not know which line needs it
DEPENDENCY_RULE = TEMPLATE(
    "Write the dependency rule in a paragraph. Name which pair cannot run "
    "in parallel and why.",
    example="A pair may share a turn only when neither needs the other's "
            "output. get_claim runs alone. The policy lookup, the hospital "
            "lookup and one check_coverage per line are mutually independent "
            "and share turn 2. get_preauthorisation cannot join them: which "
            "line needs one is not known until check_coverage has answered.")

# Each tool's prerequisites, as {tool: [whose output it needs]}.
# The framework uses this to check that the turn grouping in your scripts
# is actually legal.
DEPENDS_ON = {
    "get_claim": TEMPLATE("Whose output does it depend on? Entry tool: []",
                          example=[]),
    "lookup_policy": TEMPLATE("Depends on whom?", example=["get_claim"]),
    "check_coverage": TEMPLATE(
        "Depends on whom? Note that it needs policy_id."),
    "get_preauthorisation": TEMPLATE(
        "Depends on whom? This is the critical row."),
    "check_duplicate_claim": TEMPLATE("Depends on whom?"),
    "issue_decision_letter": TEMPLATE("Depends on whom?"),
}

# Two honest limits — the report requires them, and "we expect you to
# find them".
PARALLEL_LIMITS = {
    "unnecessary_calls": TEMPLATE(
        "When does parallel become more expensive? Hint: in serial, an "
        "early observation can tell you to skip a later call. The "
        "scaffold REF example has a speculative dual-window query. On "
        "Problem A: CLM-8925 exits early after two turns on the annual "
        "limit — if you fire every coverage check in parallel, those "
        "calls are wasted.",
        example="On CLM-8925 the annual limit is breached at turn 2. A "
                "sequential agent stops there; one that fired every coverage "
                "check in parallel has paid for four lookups it will never "
                "use."),
    "removed_decision_point": TEMPLATE(
        "Parallel removes a decision point the model would otherwise use. "
        "Where does your dependency rule draw the line, and why?",
        example="We batch only within a dependency level, never across one, "
                "so the model still gets to decide after every level."),
}

PARALLEL_CORRECTNESS = TEMPLATE(
    "Did pass rate change after going parallel? If not, say so; if it "
    "did, explain. The framework measures the number; you explain it.",
    example="Unchanged at 40/40. Regrouping calls does not change what any "
            "of them returns.")
