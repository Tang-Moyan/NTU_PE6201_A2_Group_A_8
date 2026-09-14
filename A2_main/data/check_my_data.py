#!/usr/bin/env python3
"""
PE6201 · A2 — check your data
=============================
RUN THIS EVERY TIME YOU ADD RECORDS.

    python3 check_my_data.py

It catches the four things that go wrong when a team extends the fixture data,
and it catches them in seconds rather than in an evening of debugging an agent
that is behaving perfectly.

  1. AN ID THAT RESOLVES TO NOTHING.
     A claim whose member_id matches no member. A line naming a procedure code
     that does not exist. Your tool returns nothing, your agent reasons about
     nothing, and the run looks superficially fine. This is the single most
     expensive mistake available to you here, and it is completely silent.

  2. A SHIPPED RECORD THAT CHANGED.
     The records we gave you are the ones a marker re-runs your harness against,
     and the answer key is written against them. Add freely; edit nothing. This
     script holds a fingerprint of every shipped row and will tell you exactly
     which one moved.

  3. A DUPLICATE ID.
     Two claims called CLM-9001. One of them is invisible.

  4. A CASE WITH NO LABEL, OR A LABEL WITH NO CASE.
     An unlabelled case cannot be scored. A label pointing at a record you
     deleted is worse - it looks like a pass rate and is not one.

It does NOT check whether your labels are RIGHT. That judgement is yours, and it
is a large part of what D4 is marked on.

Exit code 0 = your data hangs together.
"""

import json
import os
import sys
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))

# Which field identifies a row, per table. A tuple means the id is composite.
IDS = {
    "procedures": "code", "hospitals": "hospital_id", "policies": "policy_id",
    "members": "member_id", "preauthorisations": "preauth_id",
    "claims": "claim_id", "decided_claims": "claim_id",
    "required_documents": "procedure_code",
}

# (table, path to the id inside a row, table it must exist in, that table's key).
# "lines[].code" means: for each item in the row's `lines` list, take `code`.
LINKS = {
    "A": [
        ("claims", "member_id", "members", "member_id"),
        ("claims", "hospital_id", "hospitals", "hospital_id"),
        ("claims", "lines[].code", "procedures", "code"),
        ("members", "policy_id", "policies", "policy_id"),
        ("preauthorisations", "member_id", "members", "member_id"),
        ("preauthorisations", "procedure_code", "procedures", "code"),
        ("policies", "exclusions[].code", "procedures", "code"),
        ("required_documents", "procedure_code", "procedures", "code"),
        ("decided_claims", "member_id", "members", "member_id"),
        ("decided_claims", "lines[].code", "procedures", "code"),
    ],
}

QUEUE = {"A": ("claims", "claim_id")}
DECISIONS = {
    "A": {"approve_in_principle", "request_document", "escalate"},
}

problems, warnings = [], []


def fail(msg):
    problems.append(msg)


def warn(msg):
    warnings.append(msg)


def load(letter, name):
    path = os.path.join(HERE, "data_%s" % letter, name + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def row_id(table, row):
    k = IDS[table]
    if isinstance(k, tuple):
        return "|".join(str(row.get(x, "?")) for x in k)
    return str(row.get(k, "?"))


def fingerprint(row):
    return hashlib.sha1(
        json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:10]


def values_at(row, path):
    """Resolve 'lines[].code' or 'member_id' to a list of values."""
    if "[]." in path:
        outer, inner = path.split("[].")
        return [item.get(inner) for item in row.get(outer, []) or []]
    v = row.get(path)
    return [] if v is None else [v]


# ─────────────────────────────────────────────────────────────────────────────
def check_problem(letter):
    tables = {}
    for table in [t for t in IDS if t in [x[0] for x in LINKS[letter]]
                  or t in [x[2] for x in LINKS[letter]]
                  or t == QUEUE[letter][0]]:
        rows = load(letter, table)
        if rows is not None:
            tables[table] = rows
    if not tables:
        return False

    print("\nProblem %s" % letter)
    for name in sorted(tables):
        print("   %4d  %s" % (len(tables[name]), name))

    # 3 · duplicate ids ------------------------------------------------------
    for table, rows in tables.items():
        seen = {}
        for row in rows:
            rid = row_id(table, row)
            if rid in seen:
                fail("%s: TWO rows share the id %r. One of them can never be found."
                     % (table, rid))
            seen[rid] = row

    # 1 · every id resolves --------------------------------------------------
    for src, path, dst, dstkey in LINKS[letter]:
        if src not in tables or dst not in tables:
            continue
        known = {r.get(dstkey) for r in tables[dst]}
        for row in tables[src]:
            for v in values_at(row, path):
                if v not in known:
                    fail("%s %s: %s = %r does not exist in %s.json"
                         % (src, row_id(src, row), path, v, dst))

    # 2 · shipped rows unchanged ---------------------------------------------
    shipped = SHIPPED.get(letter, {})
    for table, prints in shipped.items():
        if table not in tables:
            fail("%s.json is missing entirely." % table)
            continue
        have = {row_id(table, r): fingerprint(r) for r in tables[table]}
        for rid, fp in prints.items():
            if rid not in have:
                fail("%s: shipped row %r has been DELETED. Add records, remove none."
                     % (table, rid))
            elif have[rid] != fp:
                fail("%s: shipped row %r has been EDITED. The answer key is written "
                     "against the original." % (table, rid))

    # a few things that are legal but almost always a mistake ----------------
    if letter == "A" and "preauthorisations" in tables:
        needs = {p["code"] for p in tables.get("procedures", [])
                 if p.get("requires_preauth")}
        for pa in tables["preauthorisations"]:
            if pa.get("procedure_code") not in needs:
                warn("preauthorisations %s authorises %s, but that procedure does "
                     "not require one - your agent will never look for it."
                     % (pa.get("preauth_id"), pa.get("procedure_code")))

    # 4 · labels ---------------------------------------------------------------
    qtable, qkey = QUEUE[letter]
    keypath = os.path.join(HERE, "expected_outcomes_%s.json" % letter)
    if not os.path.exists(keypath):
        warn("expected_outcomes_%s.json not found - skipping the label check." % letter)
        return True
    with open(keypath, encoding="utf-8") as fh:
        key = json.load(fh)
    labelled = {}
    for row in key:
        cid = row.get("case_id")
        if cid in labelled:
            fail("answer key %s: %r is labelled twice." % (letter, cid))
        labelled[cid] = row
    cases = {r[qkey] for r in tables.get(qtable, [])}

    for cid in sorted(cases - set(labelled)):
        fail("%s has no label in expected_outcomes_%s.json - it cannot be scored."
             % (cid, letter))
    for cid in sorted(set(labelled) - cases):
        fail("expected_outcomes_%s.json labels %r, but no such record exists."
             % (letter, cid))

    for cid, row in labelled.items():
        dec = row.get("expected_decision")
        if dec not in DECISIONS[letter]:
            fail("%s: expected_decision %r is not one of %s"
                 % (cid, dec, sorted(DECISIONS[letter])))
        if dec == "escalate" and not row.get("trigger"):
            fail("%s: an escalation with no single trigger. Which one rule sent it "
                 "to a human?" % cid)
        if dec == "request_document" and not row.get("missing"):
            fail("%s: a request with nothing named. \"More information required\" "
                 "scores nothing." % cid)
    return True


def main():
    print("Checking your fixture data …")
    found = [l for l in ("A",) if check_problem(l)]
    if not found:
        sys.exit("\nNo data_A/ found. Run the generator first.")

    print()
    for w in warnings:
        print("  note  " + w)
    for p in problems:
        print("  FAIL  " + p)

    if problems:
        print("\n%d problem(s). Fix these before you trust a single result."
              % len(problems))
        return 1
    print("\nYour data hangs together%s." %
          ("  (%d note(s) above)" % len(warnings) if warnings else ""))
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Fingerprints of the rows we shipped. Generated - do not edit by hand.
# ─────────────────────────────────────────────────────────────────────────────
SHIPPED = json.loads(r"""{
 "A": {
  "claims": {
   "CLM-8842": "4ad613af83",
   "CLM-8850": "5a40474c46",
   "CLM-8861": "9ec4a51f5c",
   "CLM-8874": "eb5e59f6f7",
   "CLM-8888": "330ac54920",
   "CLM-8894": "6fea844b05",
   "CLM-8901": "14573662c5",
   "CLM-8910": "cd160f79c6",
   "CLM-8917": "ab38b18cf0",
   "CLM-8925": "7f349c185c",
   "CLM-8933": "d36eac8df2",
   "CLM-8941": "5f1ca5d4b3",
   "CLM-8952": "6aeeb8f5de",
   "CLM-8960": "ca977e2e1a",
   "CLM-8971": "32bf06058b"
  },
  "decided_claims": {
   "CLM-8688": "1557c774fc",
   "CLM-8702": "51009fa4e1",
   "CLM-8710": "b59c76cf52",
   "CLM-8726": "22bd7f6199"
  },
  "hospitals": {
   "H-114": "a1dbe4a468",
   "H-207": "74454f8d00",
   "H-330": "f50ad97715",
   "H-451": "d9b5656204"
  },
  "members": {
   "M-2214": "49a60192ef",
   "M-3390": "96485ee473",
   "M-4471": "8146213bd4",
   "M-5502": "4d2c6d9788",
   "M-6118": "883972e3cb"
  },
  "policies": {
   "POL-3310": "464995abe8",
   "POL-4102": "66228cb99e",
   "POL-5588": "cce631a8d4",
   "POL-6001": "3e16b7eec4",
   "POL-7220": "92dc4236d4"
  },
  "preauthorisations": {
   "PA-5521": "4c5917615f",
   "PA-5640": "36233b727c",
   "PA-5702": "b5350316ee"
  },
  "procedures": {
   "15823": "73c4a0ad79",
   "27447": "41ca014e93",
   "29881": "b1d81f9960",
   "31255": "4e43bd0d72",
   "45378": "7026e469a0",
   "47120": "2f536751d7",
   "62480": "5b1d8a32cd",
   "70553": "a524cc31cc",
   "80053": "4169960807",
   "99213": "cb8ed69b10"
  },
  "required_documents": {
   "27447": "73a06f541d",
   "45378": "ef05d66e89",
   "62480": "1f8dc2fe38"
  }
 }
}
""")


if __name__ == "__main__":
    sys.exit(main())
