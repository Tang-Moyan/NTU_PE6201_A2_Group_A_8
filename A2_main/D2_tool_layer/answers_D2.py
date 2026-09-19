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
    {"before": "check_coverage(code)",
     "after": "check_coverage(code, policy_id)",
     "makes_impossible": (
         "Checking coverage against no policy at all and getting a "
         "confident answer about nothing."
     )},
    {"before": "get_preauthorisation(member_id, procedure_code)",
     "after": "get_preauthorisation(member_id, procedure_code, date_of_service)",
     "makes_impossible": (
         "Looking up a pre-authorisation without the treatment date, so an "
         "expired approval could silently look valid."
     )},
]

DESCRIPTOR_EXPERIMENT_TOOL = "get_preauthorisation"

DESCRIPTOR_V1 = {
    "name": "get_preauthorisation",
    "purpose": "Look up a pre-authorisation.",
    "when": "When you need one.",
    "args": {"member_id": "str", "procedure_code": "str",
             "date_of_service": "str"},
    "returns": "the pre-authorisation or null",
    "failure": "Returns null.",
}


def v1_return(tool_name, args, result):
    """v1 return shape: deliberately fatter than the v2 projection."""
    if tool_name != "get_preauthorisation":
        return result
    from D2_tool_layer import tools
    rows = tools._load("A", "preauthorisations")
    return {
        "query": args,
        "all_rows": rows,
        "match": result,
        "note": "v1 dumps the whole table and lets the model filter",
    }


DESCRIPTOR_EXPERIMENT_VERDICT = (
    "v2's descriptor is 138 tokens longer (205 vs 67) and its return is "
    "about 93% smaller (21 vs 296 avg tokens per call). The longer "
    "descriptor is paid once per turn; the fat v1 return compounds because "
    "every observation is re-sent on later turns. Guardrail cases stayed "
    "10/10. Evaluation pass rate is not measurable on the scripted "
    "backend - take it from the D5 live battery on one fixed model. A "
    "prompt instruction is paid on every call, every run, forever, and "
    "dies when you change models; an interface constraint is paid once "
    "and holds permanently - which is why the return-shape cut, not the "
    "descriptor length, is the dominant D2(b) saving."
)


DEPENDENCY_RULE = (
    "A pair may share a turn only when neither needs the other's output. "
    "get_claim runs alone. lookup_policy, one check_coverage per line, and "
    "check_duplicate_claim are mutually independent and share turn 2. "
    "get_preauthorisation cannot join them: which line needs one is not "
    "known until check_coverage has answered. issue_decision_letter is "
    "last and gated."
)

DEPENDS_ON = {
    "get_claim": [],
    "lookup_policy": ["get_claim"],
    # policy_id is required, but lookup_policy and per-line coverage are
    # independent enough to share a turn (scripts supply policy_id in-args).
    "check_coverage": ["get_claim"],
    "get_preauthorisation": ["get_claim", "check_coverage"],
    "check_duplicate_claim": ["get_claim"],
    "issue_decision_letter": ["get_claim", "check_coverage",
                              "check_duplicate_claim"],
}

PARALLEL_LIMITS = {
    "unnecessary_calls": (
        "On CLM-8925 the annual limit is breached at turn 2. A sequential "
        "agent stops there; one that fired every coverage check in parallel "
        "would have paid for line lookups it will never use."
    ),
    "removed_decision_point": (
        "We batch only within a dependency level, never across one, so the "
        "model still gets to decide after every level - in particular after "
        "coverage, before pre-authorisation."
    ),
}

PARALLEL_CORRECTNESS = (
    "On the current scripted set, packing independent calls does not change "
    "what any tool returns; pass rate stays at 100% on the parallel arm. "
    "The sequential arm on CLM-8842 is the one that fails - it hits the "
    "budget ceiling - so correctness moved because a guardrail fired, not "
    "because regrouping invented a different answer."
)
