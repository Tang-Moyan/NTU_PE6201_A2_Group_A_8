"""
D5 - TEST SCRIPT
=====================================================================
    python A2_main/D5_model_battery/test_D5.py

Two things it checks that nothing else does:

  1. VENDOR NEUTRALITY, by reading the source. Exactly one function may
     know a vendor exists. This greps the scaffold for network calls
     and fails if they are scattered.
  2. THE COMMITTED DEFAULT, by reading config.py as text rather than
     importing it. What a marker gets is what is committed, not what
     is in your shell.
=====================================================================
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common.bootstrap import A2_MAIN                           # noqa: E402
from common.checks import Checker                              # noqa: E402
from common.template import is_filled                          # noqa: E402
from D5_model_battery import answers_D5 as A                   # noqa: E402
from D5_model_battery import battery                           # noqa: E402

NETWORK = re.compile(
    r"\b(urllib\.request\.urlopen|requests\.(get|post)|http\.client|"
    r"httpx\.|aiohttp\.)")


def test_reproducible(c):
    committed = battery.scripted_default_in_file()
    c.require('committed default is BACKEND = "scripted"',
              committed == "scripted",
              'config.py says %r - a marker clones and runs it this way, and '
              'Technical Execution is capped if the numbers do not come back'
              % committed,
              ok_detail="")

    s = battery.scripted_run()
    c.require("the scripted run produces numbers", bool(s),
              "no case has both a label and a script", ok_detail=(
                  "%.1f%% over %d trial(s)" % (s["pass_rate"] * 100, s["trials"])
                  if s else ""))

    c.require("a fresh-clone test is recorded",
              is_filled(A.FRESH_CLONE_TESTED),
              "'works on my laptop' has caught out every cohort", soft=True)


def test_vendor_neutrality(c):
    """Exactly one function may know a vendor exists."""
    hits = []
    for dirpath, dirnames, filenames in os.walk(A2_MAIN):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", "output", "data")]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            for i, line in enumerate(open(path, encoding="utf-8"), 1):
                if NETWORK.search(line) and not line.strip().startswith("#"):
                    hits.append("%s:%d"
                                % (os.path.relpath(path, A2_MAIN), i))
    c.require("network access is confined to one place", len(hits) <= 1,
              "found in %s - switching vendor should be a one-string change"
              % ", ".join(hits),
              ok_detail=("at %s" % hits[0]) if hits else "none found")

    import config
    for name in ("BACKEND", "MODEL", "BASE_URL"):
        c.require("config.%s exists" % name, hasattr(config, name))


def test_battery_declared(c):
    models = battery.live_models()
    c.require("at least three models declared", len(models) >= 3,
              "%d of 3 - split them across the team, one member one key"
              % len(models), soft=True)

    slugs = [m["slug"] for m in models]
    c.require("model slugs are distinct", len(slugs) == len(set(slugs)),
              "duplicates: %s" % sorted({s for s in slugs if slugs.count(s) > 1}),
              ok_detail="")

    priced = [m for m in models
              if is_filled(m.get("price_in")) and is_filled(m.get("price_out"))]
    c.require("every declared model has both prices",
              len(priced) == len(models),
              "%d of %d priced - D6's break-even needs them"
              % (len(priced), len(models)), soft=True)

    c.require("prices were verified against a vendor page",
              is_filled(A.PRICES_VERIFIED_ON),
              "quoting a price you did not verify is what D6 marks down",
              soft=True)

    tiers = {m.get("tier") for m in models if is_filled(m.get("tier"))}
    c.require("a cheap and an expensive tier are both present",
              len(tiers) >= 2,
              "tiers declared: %s - D6's break-even compares a cheap model "
              "against an expensive one" % sorted(tiers), soft=True)


def main():
    c = Checker("D5 - the model battery")
    test_reproducible(c)
    test_vendor_neutrality(c)
    test_battery_declared(c)
    c.templates(A, "D5 answers filled")
    code = c.finish()
    print()
    print("  Scripted report:  python A2_main/D5_model_battery/battery.py")
    print("  Live battery   :  A2_LIVE=1 + OPENROUTER_API_KEY, same script")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
