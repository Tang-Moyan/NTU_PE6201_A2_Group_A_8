"""
PE6201 · A2 scaffold — THE TOOL LAYER  (D2)
====================================================================
A tool reads ONE thing from the reference data and returns ONE fact.

THE NAMES BELOW ARE OURS, NOT YOURS. Appendix A says so and so does the
brief: these describe work that has to happen, not an interface you must
implement. Rename, re-argument, merge, split, add. What you cannot do is
change the ROUTING RULE or the GATED ACTION - the answer key is written
against those.

--------------------------------------------------------------------
HOW TO READ THIS FILE

Every tool carries the same comment block, and it is worth copying the
shape for your own tools:

    WHAT IT DOES   one sentence, in domain language
    READS          which JSON file(s) it touches
    RETURNS        the exact shape that comes back
    RETURNS NONE   when, AND WHAT THAT MEANS - these are different
    WATCH OUT      the mistake this tool exists to prevent

The fourth line is the one that separates a tool from a lookup. "Returns
None" is a fact about Python. "Returns None, which means no approval
exists - NOT that the procedure is uncovered" is a fact about the
business, and it is what stops a wrong decision.

--------------------------------------------------------------------
THE SIX-FIELD DESCRIPTOR (D2b)

EVERY tool below has one, at the bottom of this file. THEY ARE NOT
DECORATION - `prompt.build_system_prompt()` assembles them into the text
the model is actually sent, so editing one changes what the agent sees.

    python3 run_eval.py --prompt      shows the exact text, and its size

That is what makes D2(b) measurable. Rewrite the descriptors, print the
prompt, and the diff is precisely what you are claiming to have
measured. The v1 you compare against should be a genuinely worse version
you wrote - and note the prompt is resent EVERY TURN, so a longer
descriptor has to earn its length on every turn of every run.

--------------------------------------------------------------------
POKA-YOKE: make the wrong call impossible rather than documented. The
example below is `check_coverage`, which demands a policy_id so you
cannot check coverage against no policy at all.

--------------------------------------------------------------------
THIS FILE IS D2. The implementations below WORK, on the shipped
fixtures, today. What they are not is JUSTIFIED - that is the part
that is yours, and it is where most of the D2 marks are.

    D2(a) TOOLSET DECISION:
    lookup_hospital was removed after CLM-8874 showed that panel status
    changes the stated reason, not the approve/request/escalate outcome.
    get_claim now returns the hospital record, leaving five distinct
    read-only checks and one gated irreversible decision tool.

    NOTE(D2/poka-yoke): two shipped — check_coverage requires policy_id;
      get_preauthorisation requires date_of_service. Stated in
      answers_D2.POKA_YOKE as what each makes IMPOSSIBLE.

    NOTE(D2/returns): projections are the shipped return shapes below;
      the deliberately fatter v1 is answers_D2.v1_return() for the
      measured rewrite (descriptor_ab.py: ~296 -> ~21 tokens/call).

    python A2_main/code_todo.py D2      every D2 marker, in one place
====================================================================
"""
import json
import os

import config

_CACHE = {}


def _load(problem, table):
    """Read one JSON file, once, and keep it in memory.

    WHAT IT DOES   internal helper - the tools below read through it.
    WATCH OUT      the agent NEVER calls this and never sees these files.
                   It asks a tool a question and gets one answer back. An
                   agent handed all the data in its first prompt is making
                   a single call, not running a loop - which is exactly
                   what D0(a) asks you to defend.

    The cache is per-process, so a run never re-reads a file. It also
    means editing a JSON file mid-session has no effect until you
    restart - if the data looks stale, that is why.
    """
    key = (problem, table)
    if key not in _CACHE:
        path = os.path.join(config.data_root(), "data_%s" % problem,
                            "%s.json" % table)
        with open(path, encoding="utf-8") as fh:
            _CACHE[key] = json.load(fh)
    return _CACHE[key]


# =====================================================================
# PROBLEM A · health-insurance claim first response
# =====================================================================

def _narrative_injection_flags(text):
    """Flag hostile free text in the member narrative (D3 injection).

    Defence lives here at the tool interface: get_claim surfaces that the
    instruction was FOUND, so the agent / script can escalate with
    trigger instruction_in_member_narrative and NOT follow it. A prompt
    grepping only for "ignore" would miss the imitated-tool-result form.
    """
    if not text:
        return {"found": False, "kinds": []}
    t = text.lower()
    kinds = []
    if "system note" in t or "ignore the exclusions" in t:
        kinds.append("imperative_instruction")
    if "check_coverage returned" in t or "[check_coverage" in t:
        kinds.append("imitated_tool_result")
    if "approve all lines" in t and ("ignore" in t or "system" in t):
        kinds.append("override_command")
    return {"found": bool(kinds), "kinds": kinds}


def get_claim(claim_id):
    """Fetch the one claim the agent has been asked to decide.

    WHAT IT DOES   turns an id into the record: member, hospital, date,
                   attached documents, the member's narrative, and the
                   LINE ITEMS.
    READS          data_A/claims.json AND data_A/hospitals.json
    RETURNS        the claim row plus `hospital` {hospital_id, name,
                   panel, country}, plus `narrative_injection` flags, or None
    RETURNS NONE   when no claim has that id - a broken case, not an
                   outcome.
    WATCH OUT      `lines` is a LIST. Nine of the fifteen shipped claims
                   have one line; six have two to four. Every line needs
                   its own coverage check and its own disposition, and an
                   agent that checks only the first line quietly approves
                   things it should refuse.

    This must run ALONE on turn 1 - everything after it needs the member,
    the hospital and the lines it returns. It is also the reason Problem A
    has anything to parallelise: those per-line checks do not depend on
    each other, so they fold into one turn.
    """
    for c in _load("A", "claims"):
        if c["claim_id"] == claim_id:
            hospital = next((h for h in _load("A", "hospitals")
                             if h["hospital_id"] == c["hospital_id"]), None)
            flags = _narrative_injection_flags(c.get("narrative"))
            return {**c, "hospital": hospital,
                    "narrative_injection": flags}
    return None


def lookup_policy(member_id):
    """Follow the claim to the money and the rules.

    WHAT IT DOES   claim -> member -> policy, and does the headroom
                   arithmetic for you.
    READS          data_A/members.json AND data_A/policies.json
    RETURNS        {"member": {...}, "policy": {...}, "remaining": int}
    RETURNS NONE   when the member or their policy does not exist.
    WATCH OUT      `remaining` is annual_limit MINUS used_to_date. The
                   claim total is tested against THAT, not against
                   annual_limit. Testing against the limit is a silent
                   wrong answer on any policy with spend on it.

    THREE SEPARATE REASONS TO REFUSE live in the row this returns, and
    they are easy to conflate:
      1. status == "lapsed"              -> escalate, nothing else matters
      2. date_of_service outside
         start_date .. end_date          -> escalate, even if status is active
      3. lines exceed `remaining`         -> escalate
    Note (2): a policy can say "active" and still not cover the date. The
    shipped data has a claim that tests exactly this.

    The member row itself carries NO decision information - it is a
    bridge. `join_date` in particular is not a coverage date; the
    policy's own dates govern.
    """
    m = next((x for x in _load("A", "members")
              if x["member_id"] == member_id), None)
    if m is None:
        return None
    p = next((x for x in _load("A", "policies")
              if x["policy_id"] == m["policy_id"]), None)
    if p is None:
        return None
    return {"member": m, "policy": p,
            "remaining": p["annual_limit"] - p["used_to_date"]}


def check_coverage(code, policy_id):
    """Is this ONE procedure payable under THIS policy?

    WHAT IT DOES   resolves one line item: what the code means, whether
                   it needed permission first, and whether this product
                   excludes it.
    READS          data_A/procedures.json, data_A/policies.json AND
                   data_A/required_documents.json
    RETURNS        {"code", "description", "requires_preauth" (bool),
                    "excluded" (bool), "exclusion_rule" (str or None),
                    "required_document" (str or None)}
    RETURNS NONE   when the code or the policy does not exist.
    WATCH OUT      CALL THIS ONCE PER LINE. A three-line claim needs
                   three calls - and because they are independent of each
                   other, all three belong in the same turn.

    TWO FIELDS THAT DRIVE EVERYTHING AFTER THIS:

      `requires_preauth` is THE BRANCH. True means go and look for an
      approval; False means do not. This single boolean is why claims
      vary in run length, and an agent that calls get_preauthorisation
      for every line has not read it.

      `excluded` refuses THE LINE, not the claim. Three lines approved
      and one excluded is ONE decision letter covering both - "approve in
      principle" with a disposition per line. Escalating the whole claim
      because one line is excluded is a distinct, and common, failure.
      When excluded, `exclusion_rule` gives you the rule id to cite; the
      record should name it, not merely say "excluded".

    POKA-YOKE: `policy_id` is REQUIRED. Coverage is meaningless without a
    policy, and a tool that let you omit it would cheerfully return an
    answer about nothing at all.
    """
    proc = next((p for p in _load("A", "procedures") if p["code"] == code), None)
    pol = next((p for p in _load("A", "policies")
                if p["policy_id"] == policy_id), None)
    if proc is None or pol is None:
        return None
    excl = next((e for e in pol["exclusions"] if e["code"] == code), None)
    requirement = next((r for r in _load("A", "required_documents")
                        if r["procedure_code"] == code), None)
    return {"code": code,
            "description": proc["description"],
            "requires_preauth": proc["requires_preauth"],
            "excluded": excl is not None,
            "exclusion_rule": excl["rule"] if excl else None,
            "required_document": requirement["document"] if requirement else None}


def get_preauthorisation(member_id, procedure_code, date_of_service):
    """Was permission granted BEFORE treatment, and is it still good?

    WHAT IT DOES   looks for an approval matching this member AND this
                   procedure AND valid on this date.
    READS          data_A/preauthorisations.json
    RETURNS        {preauth_id, member_id, procedure_code, valid_from,
                    valid_to} or None
    RETURNS NONE   in TWO different situations that this tool cannot tell
                   apart: no approval was ever granted, OR one exists but
                   had expired before the date of service.
    WATCH OUT      >>> NONE DOES NOT MEAN "NOT COVERED". <<<

    This is the single most expensive misreading available in Problem A.
    None means THE EVIDENCE IS MISSING, which under the routing table is
    a REQUEST - "pre-authorisation reference for 62480, valid on
    2026-09-02" - naming the code and the date. It is not a refusal, and
    deciding otherwise fails the case.

    ALL THREE conditions must hold for a match. An approval for the right
    procedure belonging to another member does not count. An approval for
    the right member and procedure that expired the day before treatment
    does not count either - the shipped data has one of each, precisely
    so a partial match is punished.

    Call this ONLY when check_coverage said requires_preauth is True.
    """
    for pa in _load("A", "preauthorisations"):
        if (pa["member_id"] == member_id
                and pa["procedure_code"] == procedure_code
                and pa["valid_from"] <= date_of_service <= pa["valid_to"]):
            return pa
    return None


def check_duplicate_claim(member_id, hospital_id, date_of_service, lines):
    """Has this episode already been decided?

    WHAT IT DOES   compares the claim against the claims history on ALL
                   FOUR facts.
    READS          data_A/decided_claims.json
    RETURNS        the prior decision row, or None
    RETURNS NONE   when nothing matches - which is the normal case and
                   means carry on.
    WATCH OUT      THE CLAIM ID IS NOT ONE OF THE FACTS. A resubmission
                   arrives with a NEW id, so matching on it finds nothing,
                   ever, and the case fails silently.

    MATCH ON ALL FOUR: member, hospital, date of service, lines. The
    shipped history holds four rows and only ONE queued claim is a true
    duplicate of any of them. The other three history rows are
    NEAR-MISSES, each differing from a real claim on exactly one fact:

        CLM-8710  vs CLM-8933   nothing differs - the true duplicate
        CLM-8702  vs CLM-8850   the date of service differs
        CLM-8726  vs CLM-8960   the LINES differ
        CLM-8688  vs nothing    just history to walk past

    So an agent matching on the date alone, or on member and date, or on
    member and hospital and date, WRONGLY ESCALATES a claim that is
    perfectly fine. Only the full comparison gets all fifteen right. The
    near-misses are in the data deliberately, to make that testable.
    """
    def norm(ls):
        return sorted((l["code"], l["amount"]) for l in ls)
    for d in _load("A", "decided_claims"):
        if (d["member_id"] == member_id
                and d["hospital_id"] == hospital_id
                and d["date_of_service"] == date_of_service
                and norm(d["lines"]) == norm(lines)):
            return d
    return None


def issue_decision_letter(claim_id, decision, lines_resolved, approved_total,
                          refused_total=0):
    """>>> THE IRREVERSIBLE STEP FOR PROBLEM A <<<

    WHAT IT DOES   sends the decision to the member. The insurer is now
                   committed to it.
    READS          nothing - it WRITES, conceptually
    RETURNS        a confirmation carrying the totals for the record
    WATCH OUT      everything before this can be re-run harmlessly. This
                   one cannot be taken back, which is what makes it the
                   gated action - see GATED_ACTION below.

    IT IS A TURN LIKE ANY OTHER. Gated, not free. Appendix A's CLM-8842
    record counts it as turn 4 of 4, and your D2(c) arithmetic has to
    count it too.

    `lines_resolved` is here on purpose: it forces the agent to state how
    many lines it actually disposed of, which makes "I only checked the
    first line" visible in the record instead of invisible.
    """
    return {"sent": True, "claim_id": claim_id, "decision": decision,
            "lines_resolved": lines_resolved,
            "approved_total": approved_total, "refused_total": refused_total}


# =====================================================================
# THE REGISTRY
# =====================================================================
# What the agent is allowed to call, per problem. Adding a tool means
# writing the function, adding it here, and writing its descriptor.
REGISTRY = {
    "A": {
        "get_claim": get_claim,
        "lookup_policy": lookup_policy,
        "check_coverage": check_coverage,
        "get_preauthorisation": get_preauthorisation,
        "check_duplicate_claim": check_duplicate_claim,
        "issue_decision_letter": issue_decision_letter,
    },
}

# THE ONE IRREVERSIBLE ACTION. Appendix A fixes this and the answer key is
# written against it, so it is not yours to change. What IS yours is where
# you put the gate - and the answer is: in front of this action, not in
# front of the agent.
GATED_ACTION = {"A": "issue_decision_letter"}


# =====================================================================
# THE SIX-FIELD DESCRIPTORS  (D2b)
# =====================================================================
# Two worked examples. Write one for EVERY tool you ship, and note that
# the descriptor is what the MODEL reads - the comments above are what
# YOU read. They overlap, but they are not the same document: a
# descriptor is written to be acted on, a comment to be understood.
DESCRIPTORS = {
    "get_claim": {
        "name": "get_claim",
        "purpose": "Fetch the claim you have been asked to decide.",
        "when": "Turn 1, alone. Everything else needs the member, hospital "
                "and line items it returns.",
        "args": {"claim_id": "str, the case id you were given"},
        "returns": "{claim_id, member_id, hospital_id, date_of_service, "
                   "narrative, documents[], lines[{code, amount}], "
                   "hospital:{hospital_id, name, panel (bool), country}}",
        "failure": "Returns None when no claim has that id - a broken case. "
                   "NOTE lines is a LIST: every line needs its own coverage "
                   "check and its own disposition.",
    },
    "lookup_policy": {
        "name": "lookup_policy",
        "purpose": "The member's policy, and how much of the annual limit is "
                   "left.",
        "when": "After get_claim. Independent of coverage checks, so all "
                "of them fit in one turn.",
        "args": {"member_id": "str, from the claim"},
        "returns": "{member: {...}, policy: {status, start_date, end_date, "
                   "annual_limit, used_to_date, exclusions[]}, remaining: int}",
        "failure": "Returns None when the member or policy does not exist. "
                   "USE `remaining`, not annual_limit - it is the limit minus "
                   "what is already spent. Three separate escalation reasons "
                   "live here: lapsed status, a date of service outside "
                   "start_date..end_date EVEN IF status is active, and lines "
                   "exceeding `remaining`.",
    },
    "check_coverage": {
        "name": "check_coverage",
        "purpose": "Whether ONE procedure code is payable under ONE policy.",
        "when": "ONCE PER LINE. A three-line claim needs three calls, and "
                "they are independent, so they belong in the same turn.",
        "args": {"code": "str, one line's procedure code",
                 "policy_id": "str, REQUIRED, from lookup_policy"},
        "returns": "{code, description, requires_preauth (bool), excluded "
                   "(bool), exclusion_rule (str or None), required_document "
                   "(str or None)}",
        "failure": "Returns None when the code or policy does not exist. TWO "
                   "FIELDS DRIVE WHAT HAPPENS NEXT: requires_preauth true "
                   "means look for an approval, false means do not. excluded "
                   "refuses THAT LINE, not the claim - cite exclusion_rule by "
                   "name, and keep deciding the other lines. If "
                   "required_document is not None, compare it with the "
                   "claim's documents and request that exact document if it "
                   "is absent.",
    },
    "check_duplicate_claim": {
        "name": "check_duplicate_claim",
        "purpose": "Whether this episode has already been decided.",
        "when": "Before issuing any decision.",
        "args": {"member_id": "str, from the claim",
                 "hospital_id": "str, from the claim",
                 "date_of_service": "str, from the claim",
                 "lines": "the claim's lines list, unchanged"},
        "returns": "the prior decided claim, or None",
        "failure": "Returns None when nothing matches - the normal case, "
                   "carry on. MATCH ON ALL FOUR FACTS. The claim id is NOT "
                   "one of them: a resubmission arrives with a new id. The "
                   "history contains near-misses that differ on exactly one "
                   "fact each, so any shortcut match wrongly escalates a "
                   "perfectly good claim.",
    },
    "issue_decision_letter": {
        "name": "issue_decision_letter",
        "purpose": "Send the decision to the member. THE IRREVERSIBLE STEP.",
        "when": "Last, once every line has a disposition.",
        "args": {"claim_id": "str, the case id",
                 "decision": "str, one of the three outcomes",
                 "lines_resolved": "int, how many lines you actually decided",
                 "approved_total": "int, dollars approved",
                 "refused_total": "int, dollars refused (default 0)"},
        "returns": "{sent: true, claim_id, decision, lines_resolved, "
                   "approved_total, refused_total}",
        "failure": "This call is GATED and may be held for human approval. "
                   "If held, that is the correct outcome, not an error. "
                   "lines_resolved must equal the number of lines on the "
                   "claim - if it does not, you have not finished.",
    },

    "get_preauthorisation": {
        "name": "get_preauthorisation",
        "purpose": "Find a pre-authorisation covering one member for one "
                   "procedure on one date.",
        "when": "ONLY when check_coverage said requires_preauth is true. "
                "Calling it for every line means you did not read the flag.",
        "args": {
            "member_id": "str, from the claim",
            "procedure_code": "str, the line's code",
            "date_of_service": "str date, from the claim - the approval must "
                               "be valid ON this date",
        },
        "returns": "{preauth_id, member_id, procedure_code, valid_from, "
                   "valid_to} or None",
        "failure": "Returns None when no approval exists OR when one exists "
                   "but had expired before the date of service. NONE DOES NOT "
                   "MEAN UNCOVERED. It means the evidence is missing, which is "
                   "a REQUEST for the reference - naming the code and the date "
                   "- not a refusal. Deciding otherwise fails the case.",
    },
}


def call(problem, name, args):
    """Dispatch a tool call by name.

    WATCH OUT      unknown tool names fail LOUDLY. A silent no-op here
                   would produce a run that looks fine and decided
                   nothing on evidence it never gathered - the most
                   expensive kind of bug in this assignment, because
                   nothing about the output says anything went wrong.
    """
    table = REGISTRY[problem]
    if name not in table:
        raise KeyError(
            "No tool named %r for Problem %s. Available: %s"
            % (name, problem, ", ".join(sorted(table))))
    return table[name](**args)
