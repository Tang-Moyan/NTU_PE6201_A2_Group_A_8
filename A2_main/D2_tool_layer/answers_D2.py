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
         "Calling check_coverage with no policy at all and receiving a "
         "confident-looking answer about nothing. Coverage only means "
         "anything relative to a specific policy's exclusions, so without "
         "a required policy_id the function could not honestly answer "
         "the question it claims to answer."
     )},
    {"before": "get_preauthorisation(member_id, procedure_code)",
     "after": "get_preauthorisation(member_id, procedure_code, date_of_service)",
     "makes_impossible": (
         "Checking for a pre-authorisation without pinning it to the "
         "actual treatment date. A pre-authorisation can exist for a "
         "member and a procedure but have already expired by the date "
         "of service - without date_of_service as a required argument, "
         "the function could return an approval that was valid once but "
         "is not valid now, silently turning an expired authorisation "
         "into a false positive."
     )},
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
DESCRIPTOR_EXPERIMENT_TOOL = "get_preauthorisation"

# v1: a deliberately worse six-field descriptor. Failure field collapsed
# to "Returns null" - the exact mistake Class 4 warns teams make most,
# since it hides the distinction between "never requested" and "expired".
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
    """v1 return shape: degrade v2's return into a fatter / more raw version.
    """
    if tool_name != "get_preauthorisation":
        return result
    if result is None:
        return "null"
    return (
        "Pre-authorisation record found. "
        "preauth_id=%s, member_id=%s, procedure_code=%s, "
        "valid_from=%s, valid_to=%s. This record confirms that a "
        "pre-authorisation was issued and is on file for this member "
        "and procedure, granted under standard review, subject to the "
        "usual terms and conditions of the policy in effect at the "
        "time of issuance."
        % (result["preauth_id"], result["member_id"],
           result["procedure_code"], result["valid_from"],
           result["valid_to"])
    )


DESCRIPTOR_EXPERIMENT_VERDICT = (
    "v2 is not smaller on the descriptor - it costs 138 more tokens per "
    "turn (67 vs 205), because it spells out the pre-authorisation/expired "
    "distinction instead of collapsing both into 'Returns null.' v2's "
    "RETURN is much smaller: 32 tokens per call against v1's 90. v2 has "
    "the lower per-call return cost, so its token advantage compounds as "
    "observations are carried across later turns. Net verdict: v1's "
    "smaller descriptor is not worth its bloated return. The descriptor "
    "cost is incurred as part of each turn's prompt, while the "
    "return-shape decision determines the size and clarity of every "
    "observation passed downstream. The guardrail-cases-passed number "
    "(1 of 10) is not reported here: it measures D3's code-layer "
    "guardrails, which do not read tool descriptors at all, so it cannot "
    "move between v1 and v2 and is not evidence for this experiment."
)
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
