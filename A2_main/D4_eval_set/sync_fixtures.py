"""
D4 - SYNC YOUR CASES INTO THE FIXTURES AND THE ANSWER KEY
=====================================================================
    python A2_main/D4_eval_set/sync_fixtures.py            # dry run
    python A2_main/D4_eval_set/sync_fixtures.py --write    # do it

The reference data has one entry point for new records - the EXTRA_*
lists near the bottom of make_fixtures_A.py - and one for new labels,
expected_outcomes_A.json, which is edited BY HAND on purpose because
nothing should be able to overwrite a label you reasoned about.

This script keeps both in step with answers_D4.py so six people are
not hand-editing the same two files and losing each other's rows.

WHAT IT WILL NOT DO, and these are safety rails not limitations:

  - it never touches a SHIPPED row. It rewrites only the EXTRA_* block
    and only ever APPENDS to the answer key.
  - it never invents a label. A case with no label is reported, not
    guessed. A script that could work out the right answer would be
    the agent you are being asked to build.
  - it refuses to write when a case id collides with a shipped one.

AFTER IT WRITES, run the checker - it catches the four things that go
wrong silently:

    python A2_main/data/check_my_data.py
=====================================================================
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt                                         # noqa: E402
from common.bootstrap import data_file                         # noqa: E402
from D4_eval_set import answers_D4 as A                        # noqa: E402

GENERATOR = data_file("make_fixtures_A.py")
ANSWER_KEY = data_file("expected_outcomes_A.json")

BLOCKS = [
    ("EXTRA_PROCEDURES", A.EXTRA_PROCEDURES, "list"),
    ("EXTRA_HOSPITALS", A.EXTRA_HOSPITALS, "list"),
    ("EXTRA_POLICIES", A.EXTRA_POLICIES, "list"),
    ("EXTRA_MEMBERS", A.EXTRA_MEMBERS, "list"),
    ("EXTRA_PREAUTHORISATIONS", A.EXTRA_PREAUTHORISATIONS, "list"),
    ("EXTRA_CLAIMS", A.EXTRA_CLAIMS, "list"),
    ("EXTRA_DECIDED", A.EXTRA_DECIDED, "list"),
    ("EXTRA_REQUIRED_DOCS", A.EXTRA_REQUIRED_DOCS, "dict"),
]


def _render(name, value, kind):
    """One EXTRA_* assignment, as source text."""
    if not value:
        return "%s = %s" % (name, "[]" if kind == "list" else "{}")
    body = json.dumps(value, indent=4, ensure_ascii=False)
    # json gives us true/false/null; Python wants True/False/None.
    body = re.sub(r"\btrue\b", "True", body)
    body = re.sub(r"\bfalse\b", "False", body)
    body = re.sub(r"\bnull\b", "None", body)
    return "%s = %s" % (name, body)


def planned_generator_text():
    """The generator file with the EXTRA_* block replaced."""
    src = open(GENERATOR, encoding="utf-8").read()
    for name, value, kind in BLOCKS:
        # Match `NAME = [...]` or `NAME = {...}` up to the next top-level
        # statement, tolerating the trailing shape comments that ship with
        # the file.
        pattern = re.compile(
            r"^%s\s*=\s*(\[.*?\]|\{.*?\})(?:[^\n]*)(?:\n[ \t]+#[^\n]*)*"
            % re.escape(name), re.S | re.M)
        if not pattern.search(src):
            raise SystemExit(
                "\n  Could not find %s in %s.\n"
                "  Has the generator been edited by hand? Sync expects the\n"
                "  shipped EXTRA_* block to still be there.\n"
                % (name, GENERATOR))
        src = pattern.sub(lambda _m: _render(name, value, kind), src, count=1)
    return src


def existing_ids():
    """Case ids already in the shipped data and in the answer key."""
    claims = json.load(open(data_file("data_A", "claims.json"), encoding="utf-8"))
    key = json.load(open(ANSWER_KEY, encoding="utf-8"))
    return ({c["claim_id"] for c in claims},
            {r["case_id"] for r in key})


def collisions():
    """New rows whose ids already exist. Never allowed."""
    shipped_claims, labelled = existing_ids()
    new_claims = {c.get("claim_id") for c in A.EXTRA_CLAIMS}
    # A shipped id can legitimately appear in `shipped_claims` because the
    # generator already emitted our rows on a previous sync, so compare
    # against the generator's own shipped block instead.
    src = open(GENERATOR, encoding="utf-8").read()
    head = src.split("YOUR ADDITIONS GO HERE")[0]
    shipped_only = set(re.findall(r'"claim_id":\s*"([^"]+)"', head))
    return sorted(new_claims & shipped_only)


def unlabelled():
    """New claims with no label, and labels with no claim."""
    new_claims = {c.get("claim_id") for c in A.EXTRA_CLAIMS}
    new_labels = {r.get("case_id") for r in A.EXTRA_LABELS}
    return sorted(new_claims - new_labels), sorted(new_labels - new_claims)


def planned_key():
    """The answer key with the new labels appended, shipped rows untouched."""
    key = json.load(open(ANSWER_KEY, encoding="utf-8"))
    have = {r["case_id"] for r in key}
    added = [r for r in A.EXTRA_LABELS if r.get("case_id") not in have]
    return key + added, added


def report(write=False):
    fmt.h1("D4 - sync cases into the fixtures and the answer key")

    counts = [(name, len(value)) for name, value, _ in BLOCKS]
    fmt.table(["EXTRA_* list", "rows in answers_D4"], counts, aligns=["<", ">"])

    clash = collisions()
    if clash:
        fmt.fail("id collision with SHIPPED rows: %s" % ", ".join(clash))
        print("  Add new rows with NEW ids. Never edit or delete a shipped")
        print("  row - the answer key is written against them and a marker")
        print("  re-runs your harness on them.")
        return 2

    missing_labels, orphan_labels = unlabelled()
    if missing_labels:
        fmt.todo("claims with no label: %s" % ", ".join(missing_labels))
        print("       An unlabelled case cannot be scored. Write the label")
        print("       from Appendix A's routing table BEFORE you run the")
        print("       agent - a key written from your agent's output agrees")
        print("       with itself by construction and measures nothing.")
    if orphan_labels:
        fmt.fail("labels with no claim: %s" % ", ".join(orphan_labels))
        return 2

    _, added = planned_key()
    fmt.h2("Answer key")
    fmt.kv("labels to append", len(added))
    if added:
        for row in added:
            print("      %-12s %-22s %s"
                  % (row.get("case_id"), row.get("expected_decision"),
                     row.get("family", "")))

    if not write:
        fmt.h2("Dry run - nothing written")
        print("  Re-run with --write to apply, then:")
        print("      python A2_main/data/make_fixtures_A.py")
        print("      python A2_main/data/check_my_data.py")
        return 0

    text = planned_generator_text()
    with open(GENERATOR, "w", encoding="utf-8") as fh:
        fh.write(text)
    key, _ = planned_key()
    with open(ANSWER_KEY, "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    fmt.h2("Written")
    fmt.kv("generator", GENERATOR)
    fmt.kv("answer key", "%s  (%d rows)" % (ANSWER_KEY, len(key)))
    print()
    print("  Now regenerate and check, in this order:")
    print("      python A2_main/data/make_fixtures_A.py")
    print("      python A2_main/data/check_my_data.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(report(write="--write" in sys.argv))
