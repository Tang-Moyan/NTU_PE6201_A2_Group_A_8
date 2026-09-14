"""
REPORT - ASSEMBLE THE SIX SECTIONS
=====================================================================
    python A2_main/report/assemble.py            # material + word count
    python A2_main/report/assemble.py --prose    # just the final prose

Two jobs:

  1. GATHER THE MATERIAL for each section - the answers from the right
     deliverable and the measurements from output/ - so nobody has to
     hunt for which number goes where.
  2. COUNT THE WORDS, per section and in total, against the 2,000-word
     limit. Tables and figures do not count; prose does.

WHY THE BUDGET IS SHAPED THE WAY IT IS. Sections 1 and 2 together are
850 words - nearly half - because Conceptual Understanding (25%) and
Reasoning & Justification (25%) are half the rubric, and almost all of
that lives in "why this rung" and "why this tool set". Section 5 is
short on purpose: two failures, tightly described, is more convincing
than two narrated at length.

Section 1 is read first and read hardest. A report that opens with
what the team built, rather than why an agent was the right
instrument, has skipped the question the whole of Class 4 was arranged
around.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.template import is_filled                          # noqa: E402
from report import answers_report as R                         # noqa: E402

LIMIT = 2000

SECTIONS = [
    (1, "Why an agent", 400, "D0"),
    (2, "The tool layer", 450, "D2"),
    (3, "What the evidence showed", 350, "D4 + D5"),
    (4, "What it costs", 400, "D6"),
    (5, "The two failures", 250, "D7"),
    (6, "What we would not deploy", 150, "limits + D1's alternative"),
]

PROSE = {
    1: "SECTION_1_PROSE", 2: "SECTION_2_PROSE", 3: "SECTION_3_PROSE",
    4: "SECTION_4_PROSE", 5: "SECTION_5_PROSE", 6: "SECTION_6_PROSE",
}


def material():
    """The numbers each section needs, pulled from output/."""
    ev = store.load("D4_eval") or {}
    return {
        1: _fmt_material([
            ("implied step reliability s",
             _get(store.load("D0_arithmetic"), "implied_step_reliability",
                  fmt_="%.4f")),
            ("measured pass rate P", _pct(ev.get("pass_rate"))),
            ("median turns T",
             _get(store.load("D7_turns"), "median_turns")),
            ("distinct turn counts",
             sorted({r["turns"] for r in ev.get("per_case", [])}) or None),
        ]),
        2: _fmt_material([
            ("tool block tokens",
             _get(store.load("D2_tool_audit"), "sizes", "tool_block_tokens")),
            ("whole system prompt tokens",
             _get(store.load("D2_tool_audit"), "sizes", "whole_prompt_tokens")),
            ("sequential turns / input tokens",
             _pair(store.load("D2_parallel"), "sequential")),
            ("parallel turns / input tokens",
             _pair(store.load("D2_parallel"), "parallel")),
            ("saving",
             _get(store.load("D2_parallel"), "saving", "input_tokens_pct",
                  fmt_="%.0f%% input tokens")),
            ("v2 tokens returned per call",
             _get(store.load("D2_descriptor"), "returns", "v2_avg_tokens",
                  fmt_="%.0f")),
        ]),
        3: _fmt_material([
            ("cases", ev.get("cases")),
            ("trials", ev.get("trials")),
            ("pass rate", _pct(ev.get("pass_rate"))),
            ("negative pass rate", _pct(ev.get("negative_pass_rate"))),
            ("guardrail cases held",
             _guardrails()),
            ("live models run",
             len((store.load("D5_battery") or {}).get("live") or []) or None),
        ]),
        4: _fmt_material([
            ("layer 1 per run",
             _get(store.load("D6_cost"), "baseline", "variable",
                  fmt_="US$%.5f")),
            ("layer 2 per run",
             _get(store.load("D6_cost"), "baseline", "fallback",
                  fmt_="US$%.5f")),
            ("cost per successful task",
             _get(store.load("D6_cost"), "cost_per_successful_task",
                  fmt_="US$%.5f")),
            ("monthly total",
             _get(store.load("D6_cost"), "monthly", "total_usd",
                  fmt_="US$%.2f")),
            ("break-even success rate",
             _get(store.load("D6_cost"), "break_even", "break_even",
                  fmt_="%.1f%%", scale=100)),
        ]),
        5: _fmt_material([
            ("median turns", _get(store.load("D7_turns"), "median_turns")),
            ("worst legitimate run",
             _get(store.load("D7_turns"), "worst_legitimate_turns")),
            ("runs that hit the step cap",
             _get(store.load("D7_turns"), "hit_step_cap")),
            ("failure 1 before/after turns", _failure_turns("failure_1")),
            ("failure 2 before/after turns", _failure_turns("failure_2")),
        ]),
        6: _fmt_material([
            ("limits we found", R.LIMITS_WE_FOUND),
            ("would not deploy when", R.WOULD_NOT_DEPLOY),
        ]),
    }


def _get(payload, *path, fmt_=None, scale=1):
    node = payload
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if node is None:
        return None
    if fmt_:
        try:
            return fmt_ % (node * scale)
        except (TypeError, ValueError):
            return node
    return node


def _pct(value):
    return None if value is None else "%.1f%%" % (value * 100)


def _pair(payload, arm):
    node = (payload or {}).get(arm)
    if not node:
        return None
    return "%d turns / %d tokens" % (node["total_turns"], node["tokens_in"])


def _guardrails():
    payload = store.load("D3_checklist")
    if not payload:
        return None
    held = sum(1 for r in payload["cases"] if r.get("held"))
    return "%d of %d (%d hostile-text cases)" % (held, payload["total"],
                                                 payload["hostile"])


def _failure_turns(which):
    node = (store.load("D7_failures") or {}).get(which)
    if not node:
        return None
    return "%s -> %s" % (node["before"]["turns"], node["after"]["turns"])


def _fmt_material(rows):
    return [(k, v) for k, v in rows]


def report(prose_only=False):
    fmt.h1("The report - six sections, 2,000 words of PROSE")
    fmt.kv("team", R.TEAM_ID)
    fmt.kv("problem", R.PROBLEM_CHOSEN)
    fmt.kv("repository", R.REPO_URL)

    mat = material()
    total = 0
    rows = []

    for number, title, budget, source in SECTIONS:
        text = getattr(R, PROSE[number])
        words = fmt.word_count(text) if is_filled(text) else 0
        total += words
        rows.append((number, title, budget, words or "-",
                     "over by %d" % (words - budget) if words > budget else
                     ("" if words else "not written"),
                     source))

        if prose_only:
            fmt.h2("%d · %s" % (number, title))
            fmt.paragraph(text)
            continue

        fmt.h2("%d · %s   (%d words, from %s)" % (number, title, budget, source))
        if is_filled(text):
            fmt.paragraph(text)
        else:
            print("  Prose not written. Material available:")
            for key, value in mat[number]:
                print("      %-32s %s" % (key, value if value is not None
                                          else "(not measured yet)"))

    if prose_only:
        return total

    fmt.h1("Word budget")
    fmt.table(["#", "section", "budget", "written", "note", "source"], rows,
              aligns=[">", "<", ">", ">", "<", "<"])
    print()
    fmt.kv("total prose", "%d of %d words" % (total, LIMIT))
    if total > LIMIT:
        fmt.fail("over the limit by %d words" % (total - LIMIT))
    elif total:
        fmt.ok("%d words of headroom" % (LIMIT - total))
    print()
    print("  Tables and figures do NOT count. Put every table in the")
    print("  repository and reference it - the report is argument, not data.")

    fmt.h1("The other three artefacts")
    for label, value in (("CONTRIBUTIONS.md written", R.CONTRIBUTIONS_MD_WRITTEN),
                         ("team self-appraisal done", R.SELF_APPRAISAL_DONE),
                         ("results.json committed", R.RESULTS_JSON_COMMITTED),
                         ("5-minute video", R.VIDEO_URL)):
        (fmt.ok if value is True or (is_filled(value) and value is not False)
         else fmt.todo)("%s: %s" % (label, value))
    print()
    print("  Submit as PE6201_A2_[TeamID].zip plus the video link.")
    print("  A missing self-appraisal is an INCOMPLETE SUBMISSION.")
    return total


if __name__ == "__main__":
    report(prose_only="--prose" in sys.argv)
    raise SystemExit(0)
