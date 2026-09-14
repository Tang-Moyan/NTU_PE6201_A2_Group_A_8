"""
D2(b) - THE DESCRIPTOR REWRITE, MEASURED
=====================================================================
    python A2_main/D2_tool_layer/descriptor_ab.py

D2(b) asks for one tool shipped in two versions - descriptor AND
return shape - reporting three numbers for each:

    tokens returned per call · evaluation pass rate · guardrail cases passed

WHICH OF THOSE THE SCRIPTED BACKEND CAN ANSWER, and this matters:

  tokens returned per call   YES. Exact, free, offline. The return
                             shape is our code, not the model's.
  descriptor / prompt size   YES. Exact, free, offline.
  guardrail cases passed     YES. Guardrails are code; a model has no
                             say in whether they fire.
  evaluation pass rate       NO - not scripted. The scripted backend
                             replays moves we wrote down; it never
                             consults a model, so it never READS the
                             prompt. A descriptor rewrite cannot change
                             a scripted pass rate, and reporting an
                             unchanged one as evidence would be theatre.

So this script measures three of the four for free and tells you to
take the fourth from the live battery in D5. Run it with A2_LIVE=1
once you have a key, and it will run the pass-rate arm too.

THE POINT THE MEASUREMENT EXISTS TO MAKE (Class 4 Section 7): a prompt
instruction is paid on every call of every run forever and dies when
you change model; an interface constraint is paid once and holds.
=====================================================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bootstrap import init
init()

from common import fmt, measure, store                         # noqa: E402
from common.template import is_filled                          # noqa: E402
from D2_tool_layer import answers_D2 as A                      # noqa: E402

LIVE = os.environ.get("A2_LIVE") == "1"


def v1_return_written():
    """Has the team written answers_D2.v1_return() yet?"""
    try:
        A.v1_return("probe", {}, {"x": 1})
    except NotImplementedError:
        return False
    except Exception:
        return True          # it ran and blew up on our probe - still written
    return True


# ---------------------------------------------------------------------
# descriptor size
# ---------------------------------------------------------------------
def descriptor_sizes(tool_name):
    """Prompt cost of the descriptor, v1 vs v2. Exact and free."""
    from D2_tool_layer import prompt
    from D2_tool_layer import tools
    v2 = tools.DESCRIPTORS.get(tool_name)
    if not v2:
        return None
    v2_text = prompt.format_descriptor(v2)

    if not is_filled(A.DESCRIPTOR_V1):
        return {"v2_tokens": measure.approx_tokens(v2_text),
                "v2_chars": len(v2_text), "v1_tokens": None, "v1_chars": None}

    v1_text = prompt.format_descriptor(A.DESCRIPTOR_V1)
    return {"v1_tokens": measure.approx_tokens(v1_text),
            "v1_chars": len(v1_text),
            "v2_tokens": measure.approx_tokens(v2_text),
            "v2_chars": len(v2_text)}


def whole_prompt_sizes(tool_name):
    """What the rewrite did to the WHOLE prefix, which is what gets billed."""
    from D2_tool_layer import prompt
    from D2_tool_layer import tools
    import config
    before = measure.approx_tokens(prompt.build_system_prompt(config.PROBLEM))
    if not is_filled(A.DESCRIPTOR_V1):
        return {"v2": before, "v1": None}
    original = tools.DESCRIPTORS.get(tool_name)
    try:
        tools.DESCRIPTORS[tool_name] = dict(A.DESCRIPTOR_V1)
        with_v1 = measure.approx_tokens(prompt.build_system_prompt(config.PROBLEM))
    finally:
        if original is not None:
            tools.DESCRIPTORS[tool_name] = original
    return {"v2": before, "v1": with_v1}


# ---------------------------------------------------------------------
# tokens returned per call - lever 3, and the one that compounds
# ---------------------------------------------------------------------
def return_sizes(tool_name, case_ids=None):
    """Average tokens this tool RETURNS per call, v1 vs v2.

    Lever 3 of the D6 ledger. It looks like lever 1 and is not: a fat
    tool block is linear in turns, a fat observation compounds, because
    every observation is re-sent on every later turn.
    """
    from D2_tool_layer import tools
    case_ids = case_ids or _scripted_cases()
    v2_sizes, v1_sizes = [], []
    have_v1 = v1_return_written()

    real = tools.REGISTRY["A"].get(tool_name)
    if real is None:
        return None

    captured = []

    def spy(*args, **kwargs):
        result = real(*args, **kwargs)
        captured.append((kwargs or dict(enumerate(args)), result))
        return result

    try:
        tools.REGISTRY["A"][tool_name] = spy
        from D1_agent_loop.agent import run_case
        for cid in case_ids:
            run_case(cid, problem="A")
    finally:
        tools.REGISTRY["A"][tool_name] = real

    for args, result in captured:
        v2_sizes.append(measure.approx_tokens(result))
        if have_v1:
            try:
                v1_sizes.append(
                    measure.approx_tokens(A.v1_return(tool_name, args, result)))
            except Exception as exc:                      # noqa: BLE001
                return {"error": "v1_return() raised: %s" % exc,
                        "calls": len(captured)}

    def avg(xs):
        return (sum(xs) / len(xs)) if xs else None

    return {"calls": len(captured),
            "v2_avg_tokens": avg(v2_sizes),
            "v1_avg_tokens": avg(v1_sizes) if have_v1 else None,
            "v1_written": have_v1,
            "estimated": True}


def _scripted_cases():
    from D4_eval_set import scripts
    import config
    from D4_eval_set.harness import load_cases, load_key
    key = load_key(config.PROBLEM)
    return [c for c in load_cases(config.PROBLEM)
            if c in scripts.SCRIPTS and c in key]


# ---------------------------------------------------------------------
# guardrail cases passed
# ---------------------------------------------------------------------
def guardrail_score():
    """How many D3 guardrail cases pass right now. Code, so free."""
    try:
        from D3_guardrails import checklist
    except ImportError:
        return None
    try:
        results = checklist.run_all()
    except Exception as exc:                              # noqa: BLE001
        return {"error": str(exc)}
    passed = sum(1 for r in results if r.get("held"))
    return {"passed": passed, "total": len(results)}


# ---------------------------------------------------------------------
def report():
    fmt.h1("D2(b) - the descriptor rewrite, measured")

    tool = A.DESCRIPTOR_EXPERIMENT_TOOL
    if not is_filled(tool):
        print("  Pick a tool first: DESCRIPTOR_EXPERIMENT_TOOL in answers_D2.py")
        print("  %s" % tool)
        return None

    fmt.kv("tool under test", tool)
    print()

    d = descriptor_sizes(tool)
    w = whole_prompt_sizes(tool)
    r = return_sizes(tool)
    g = guardrail_score()

    fmt.h2("1 · descriptor size - paid on EVERY turn")
    if d and d.get("v1_tokens") is not None:
        fmt.table(["version", "descriptor ~tokens", "whole prompt ~tokens"],
                  [("v1", d["v1_tokens"], w["v1"]),
                   ("v2 (shipped)", d["v2_tokens"], w["v2"])],
                  aligns=["<", ">", ">"])
        delta = d["v2_tokens"] - d["v1_tokens"]
        fmt.kv("v2 - v1", "%+d tokens on the descriptor" % delta)
        print()
        print("  This is the B in B*T + D*T(T-1)/2. A longer descriptor that")
        print("  saves one turn may still be worth it; one that saves nothing")
        print("  is pure cost, re-billed every turn of every run.")
    else:
        fmt.todo("DESCRIPTOR_V1 not written",
                 "v2 is ~%s tokens; write the deliberately worse v1"
                 % (d["v2_tokens"] if d else "?"))

    fmt.h2("2 · tokens returned per call - lever 3, and it COMPOUNDS")
    if r is None:
        fmt.fail("%s is not in the registry" % tool)
    elif r.get("error"):
        fmt.fail(r["error"])
    elif not r["v1_written"]:
        fmt.todo("v1_return() not written in answers_D2.py",
                 "v2 returns ~%.0f tokens per call over %d call(s)"
                 % (r["v2_avg_tokens"] or 0, r["calls"]))
        print("       Without it we can compare descriptors but not return")
        print("       shapes, and D2(b) asks for both.")
    else:
        fmt.table(["version", "avg ~tokens returned per call"],
                  [("v1", "%.0f" % (r["v1_avg_tokens"] or 0)),
                   ("v2 (shipped)", "%.0f" % (r["v2_avg_tokens"] or 0))],
                  aligns=["<", ">"])
        print()
        print("  Every observation is re-sent on every LATER turn, so this")
        print("  number is multiplied by the turns that follow it. A fat tool")
        print("  block is linear; a fat observation is not.")

    fmt.h2("3 · guardrail cases passed")
    if g is None:
        fmt.todo("D3 checklist not importable yet")
    elif g.get("error"):
        fmt.todo("D3 checklist not runnable yet", g["error"])
    else:
        fmt.kv("guardrail cases held", "%d of %d" % (g["passed"], g["total"]))

    fmt.h2("4 · evaluation pass rate")
    if not LIVE:
        print("  NOT MEASURABLE ON THE SCRIPTED BACKEND, and this is not a")
        print("  gap in the framework. The scripted backend replays moves you")
        print("  wrote down; it never consults a model, so it never reads the")
        print("  prompt. A descriptor rewrite cannot move a scripted pass")
        print("  rate, and reporting an unchanged one as evidence would be")
        print("  theatre.")
        print()
        print("  Take this number from the live battery:")
        print("      set A2_LIVE=1 and run A2_main/D5_model_battery/battery.py")
        print("      with v1 in place, then again with v2, on ONE fixed model.")
    else:
        print("  A2_LIVE=1. Run the battery twice - once with DESCRIPTOR_V1")
        print("  patched in, once without - on a single fixed model, and put")
        print("  both pass rates here.")

    fmt.h2("The verdict")
    fmt.paragraph(A.DESCRIPTOR_EXPERIMENT_VERDICT)

    payload = {"tool": tool, "descriptor": d, "whole_prompt": w,
               "returns": r, "guardrails": g, "live": LIVE}
    store.save("D2_descriptor", payload, source="D2/descriptor_ab.py")
    return payload


if __name__ == "__main__":
    report()
    raise SystemExit(0)
