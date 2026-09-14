"""
A2_main - THE CHECK RUNNER
=====================================================================
Every test_Dx.py is a list of checks with the same shape, so that
test_all.py can report one table across all eight deliverables.

    from common.checks import Checker

    c = Checker("D3 - guardrail layer")
    c.require("ten guardrail cases", len(CASES) >= 10,
              "you have %d" % len(CASES))
    c.templates(answers_D3)
    raise SystemExit(c.finish())

A check is one of three states, and the difference matters:

    ok      the thing is done and verified
    todo    a TEMPLATE the team has not filled in yet - expected early,
            and NOT a failure of the framework
    fail    something is wrong: an assertion broke, a count is short,
            a file the deliverable depends on is missing

`finish()` returns a process exit code: 0 only when there is neither a
todo nor a fail, so `test_all.py` can tell "not written yet" from
"written and broken" without reading the prose.
=====================================================================
"""
from common import fmt
from common.template import completeness


class Checker:
    def __init__(self, title):
        self.title = title
        self.results = []          # (state, label, detail)
        fmt.h1(title)

    # -- the three states ---------------------------------------------
    def ok(self, label, detail=""):
        self.results.append(("ok", label, detail))
        fmt.ok(label + (("  -  " + detail) if detail else ""))

    def todo(self, label, detail=""):
        self.results.append(("todo", label, detail))
        fmt.todo(label + (("  -  " + detail) if detail else ""))

    def fail(self, label, detail=""):
        self.results.append(("fail", label, detail))
        fmt.fail(label + (("  -  " + detail) if detail else ""))

    # -- the two shapes almost every check has ------------------------
    def require(self, label, condition, detail="", soft=False, ok_detail=None):
        """A hard requirement. `soft=True` reports todo instead of fail,
        for things that are simply not written yet.

        `detail` is shown on every state by default, because for most
        checks it is the observation and is worth reading either way
        ("8 tool calls in 4 turns"). Where `detail` is phrased as the
        FAILURE ("state is leaking between runs"), pass ok_detail="" so
        a passing check does not print the reason it would have failed.
        """
        if condition:
            self.ok(label, detail if ok_detail is None else ok_detail)
        elif soft:
            self.todo(label, detail)
        else:
            self.fail(label, detail)
        return bool(condition)

    def templates(self, module, label=None):
        """Report which TEMPLATE slots in an answers module are unfilled."""
        filled, total, missing = completeness(module)
        label = label or "%s answers filled" % module.__name__.split(".")[-1]
        if missing:
            self.todo(label, "%d of %d filled" % (filled, total))
            fmt.missing_report(missing)
        else:
            self.ok(label, "%d of %d filled" % (filled, total))
        return missing

    # -- the verdict ---------------------------------------------------
    def counts(self):
        c = {"ok": 0, "todo": 0, "fail": 0}
        for state, _, _ in self.results:
            c[state] += 1
        return c

    def finish(self):
        c = self.counts()
        fmt.h2("%s - %d ok, %d to do, %d failing"
               % (self.title, c["ok"], c["todo"], c["fail"]))
        if c["fail"]:
            print("  Something is WRONG, not merely unwritten. Fix the FAIL")
            print("  lines before filling in any more answers.")
            return 2
        if c["todo"]:
            print("  Nothing is broken. The TODO lines are the work left.")
            return 1
        print("  This deliverable is complete and verified.")
        return 0
