"""
A2_main - THE MEASUREMENT STORE
=====================================================================
One place where every deliverable drops the numbers it measured, and
one place where the deliverables downstream of it read them.

    store.save("D4_eval", {...})       # D4 measured a pass rate
    store.load("D4_eval")              # D0 and D6 both need it

WHY THIS EXISTS. D0's s = P^(1/T) needs D4's pass rate and D7's median
turn count. D6's layer 2 needs D4's pass rate and D5's token counts.
Passing those by hand between six people is how a report ends up with
three different pass rates in it. Everything lands in A2_main/output/
as plain JSON, and the report reads from there.

Every record carries when it was written and by which script, so a
stale number is visible rather than silently reused.
=====================================================================
"""
import datetime
import json
import os
import sys

from common.bootstrap import output_file


def save(name, payload, source=None):
    """Write one measurement record. Returns the path written."""
    path = output_file(name + ".json")
    record = {
        "name": name,
        "written_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "written_by": source or os.path.basename(sys.argv[0] or "python"),
        "payload": payload,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False, default=str)
    return path


def load(name, default=None):
    """Read one measurement record's payload, or `default` if never written."""
    path = output_file(name + ".json")
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("payload", default)


def meta(name):
    """When a record was written and by what, or None."""
    path = output_file(name + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    return {"written_at": rec.get("written_at"),
            "written_by": rec.get("written_by")}


def require(name, needed_by):
    """Load a record, or fail with the command that produces it.

    A missing upstream measurement is a normal state early on, so the
    message names the script to run rather than just raising.
    """
    payload = load(name)
    if payload is None:
        raise SystemExit(
            "\n  %s needs the measurement %r, which has not been taken yet.\n"
            "  Produce it first - see A2_main/README.md for which script\n"
            "  writes %r.\n" % (needed_by, name, name))
    return payload


def status():
    """Every record currently in output/, newest first."""
    from common.bootstrap import OUTPUT
    if not os.path.isdir(OUTPUT):
        return []
    rows = []
    for fn in sorted(os.listdir(OUTPUT)):
        if not fn.endswith(".json"):
            continue
        name = fn[:-5]
        m = meta(name) or {}
        rows.append((name, m.get("written_at", "?"), m.get("written_by", "?")))
    return rows
