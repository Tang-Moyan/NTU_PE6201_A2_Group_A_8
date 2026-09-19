"""
D5 - MERGE PER-OWNER LIVE BATTERY SHARDS
=====================================================================
    python A2_main/D5_model_battery/merge_battery.py

Each member runs with A2_OWNER set; battery.py writes

    A2_main/output/D5_battery_<Owner>.json

This script merges every shard into the single file downstream readers
use (D6, report):

    A2_main/output/D5_battery.json

Rules:
  - live rows are keyed by owner (then model). A newer shard for the
    same owner replaces that owner's previous row(s).
  - scripted summary is taken from the newest shard that has one.
  - shards are never deleted; re-run merge after anyone pushes a new one.
=====================================================================
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, store                                  # noqa: E402
from common.bootstrap import OUTPUT                            # noqa: E402


SHARD_PREFIX = "D5_battery_"
MERGED_NAME = "D5_battery"


def owner_slug(owner):
    """Safe filename fragment for an owner name."""
    raw = str(owner or "unknown").strip() or "unknown"
    out = []
    for ch in raw:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace():
            out.append("_")
    return "".join(out) or "unknown"


def shard_name(owner):
    return "%s%s" % (SHARD_PREFIX, owner_slug(owner))


def list_shard_paths():
    """Every per-owner shard on disk, excluding the merged file."""
    pattern = os.path.join(OUTPUT, SHARD_PREFIX + "*.json")
    paths = []
    for path in sorted(glob.glob(pattern)):
        base = os.path.basename(path)
        # D5_battery.json is the merge target, not a shard
        if base == MERGED_NAME + ".json":
            continue
        paths.append(path)
    return paths


def _load_file(path):
    import json
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def merge_shards(paths=None):
    """Combine shard payloads into one {scripted, live, ...} dict."""
    paths = paths if paths is not None else list_shard_paths()
    if not paths:
        return None, []

    by_owner = {}          # owner -> list of live rows (usually one)
    scripted = None
    scripted_at = ""
    sources = []

    for path in paths:
        rec = _load_file(path)
        payload = rec.get("payload") or {}
        written_at = rec.get("written_at") or ""
        sources.append((os.path.basename(path), written_at,
                        rec.get("written_by")))

        live = payload.get("live") or []
        if isinstance(live, dict):
            live = [live]
        for row in live:
            owner = row.get("owner") or "unknown"
            # Newer shard for the same owner wins entirely for that owner
            prev = by_owner.get(owner)
            if prev is None or written_at >= prev[0]:
                by_owner[owner] = (written_at, [row])

        s = payload.get("scripted")
        if s is not None and written_at >= scripted_at:
            scripted, scripted_at = s, written_at

    live_rows = []
    for owner in sorted(by_owner):
        live_rows.extend(by_owner[owner][1])

    # Stable order: follow answers_D5.MODELS owner order when possible
    try:
        from D5_model_battery import answers_D5 as A
        order = {m.get("owner"): i for i, m in enumerate(A.MODELS)}
        live_rows.sort(key=lambda r: (order.get(r.get("owner"), 999),
                                      r.get("model") or ""))
    except Exception:                                      # noqa: BLE001
        pass

    merged = {
        "scripted": scripted,
        "live": live_rows,
        "models_declared": len(live_rows),
        "merged_from": [s[0] for s in sources],
    }
    return merged, sources


def report():
    fmt.h1("D5 - merge per-owner battery shards")
    paths = list_shard_paths()
    if not paths:
        fmt.fail("no shards found",
                 "expected %s/%s<Owner>.json" % (OUTPUT, SHARD_PREFIX))
        print("  Each member runs:")
        print('    $env:A2_LIVE="1"; $env:A2_OWNER="Jojo"; '
              '$env:OPENROUTER_API_KEY="sk-or-..."')
        print("    python A2_main/D5_model_battery/battery.py")
        print("  Then commit their shard and run this merge.")
        return None

    fmt.kv("shards found", len(paths))
    for path in paths:
        print("      %s" % os.path.basename(path))

    merged, sources = merge_shards(paths)
    path = store.save(MERGED_NAME, merged, source="D5/merge_battery.py")
    print()
    fmt.ok("wrote %s" % path)
    fmt.kv("live rows", len(merged["live"]))
    for row in merged["live"]:
        print("      %-28s owner=%-10s pass=%.1f%%  neg=%s  tokens_in=%s"
              % (row.get("model"), row.get("owner"),
                 100.0 * (row.get("pass_rate") or 0),
                 ("%.1f%%" % (100.0 * row["negative_pass_rate"])
                  if row.get("negative_pass_rate") is not None else "-"),
                 row.get("tokens_in")))
    if merged.get("scripted"):
        fmt.kv("scripted pass rate",
               "%.1f%%" % (100.0 * merged["scripted"].get("pass_rate", 0)))
    print()
    print("  Commit %s plus every %s*.json shard." % (
        MERGED_NAME + ".json", SHARD_PREFIX))
    return merged


if __name__ == "__main__":
    report()
    raise SystemExit(0)
