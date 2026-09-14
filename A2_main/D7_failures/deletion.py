"""
D7 - "THE WORKING AGENT, MINUS X"
=====================================================================
D7 is specific about the shape: each failure must be built as a
DELETION FROM YOUR WORKING AGENT, not as a separately written bad
agent. Putting X back must recover the behaviour. That is what makes
it a diagnosis rather than a story.

So every deletion here is a context manager that removes ONE thing and
puts it back, and `verify_restored()` proves the second half - because
"putting X back recovers the behaviour" is a claim, and an unchecked
claim is the thing this whole assignment is about noticing.

    with deletion("dedup"):
        broken = run_case("CLM-8842")
    recovered = run_case("CLM-8842")     # must equal the original

THE THREE LAYERS a fix can belong in, and D7 marks the judgement:

    code layer       loop control, guardrails, the harness
    tool interface   signatures, return shapes, descriptors
    prompt           what the model is told

Failure 1 must be loop control (code layer). Failure 2 must NOT be -
it has to sit in the tool interface or the prompt.
=====================================================================
"""
import contextlib
import copy


LAYERS = {
    "dedup": "code",
    "step_cap": "code",
    "budget_ceiling": "code",
    "fat_observation": "tool interface",
    "weak_descriptor": "prompt",
}


@contextlib.contextmanager
def deletion(name, **options):
    """Remove one thing from the working agent, then put it back."""
    if name not in _DELETIONS:
        raise KeyError("No deletion named %r. Available: %s"
                       % (name, ", ".join(sorted(_DELETIONS))))
    with _DELETIONS[name](**options):
        yield


# ---------------------------------------------------------------------
# code layer
# ---------------------------------------------------------------------
@contextlib.contextmanager
def _delete_dedup(**_options):
    """Delete action de-duplication.

    Class 4's own worked failure. WHAT TO NOTICE: with the guard gone
    the run does not crash. No exception, no error. It repeats a call
    it already made, burns turns and tokens - AND STILL RETURNS THE
    RIGHT ANSWER. A pass-rate table would show it as a clean pass.

    Neither the step cap nor the budget ceiling necessarily fires,
    because neither is breached: they BOUND the damage, they do not
    DETECT the fault.
    """
    from D3_guardrails.guardrails import Guardrails
    real = Guardrails.check_duplicate
    Guardrails.check_duplicate = lambda self, tool, args: None
    try:
        yield
    finally:
        Guardrails.check_duplicate = real


@contextlib.contextmanager
def _delete_step_cap(**_options):
    from D3_guardrails.guardrails import Guardrails
    real = Guardrails.check_turns
    Guardrails.check_turns = lambda self, turn: None
    try:
        yield
    finally:
        Guardrails.check_turns = real


@contextlib.contextmanager
def _delete_budget(**_options):
    from D3_guardrails.guardrails import Guardrails
    real = Guardrails.check_budget
    Guardrails.check_budget = lambda self, tokens: None
    try:
        yield
    finally:
        Guardrails.check_budget = real


# ---------------------------------------------------------------------
# tool interface layer
# ---------------------------------------------------------------------
@contextlib.contextmanager
def _fatten_observation(tool="check_coverage", padding_rows=40, **_options):
    """Make one tool return the fat, unfiltered thing it used to.

    Class 4's second worked example was a 246-token stale observation
    carrying a landmine - a confident wrong answer, fixed AT THE
    INTERFACE rather than by adding a sentence to the prompt.

    This deletion removes the filtering from a tool's return: instead
    of the projection the agent needs, it gets the whole table and is
    left to find the row itself.
    """
    from D2_tool_layer import tools
    real = tools.REGISTRY["A"].get(tool)
    if real is None:
        raise KeyError("no tool named %r to fatten" % tool)

    def fat(*args, **kwargs):
        result = real(*args, **kwargs)
        if result is None:
            return None
        rows = tools._load("A", "procedures") + tools._load("A", "policies")
        return {"result": result,
                "context_you_did_not_ask_for": rows[:padding_rows]}

    tools.REGISTRY["A"][tool] = fat
    try:
        yield
    finally:
        tools.REGISTRY["A"][tool] = real


# ---------------------------------------------------------------------
# prompt layer
# ---------------------------------------------------------------------
@contextlib.contextmanager
def _weaken_descriptor(tool="get_preauthorisation", descriptor=None, **_opts):
    """Replace one descriptor with a deliberately worse one.

    Only bites on the LIVE backend: the scripted backend never consults
    a model, so it never reads the prompt. The measurable effect
    offline is the prompt size; the behavioural effect needs D5's
    battery. Say which you are reporting.
    """
    from D2_tool_layer import tools
    real = tools.DESCRIPTORS.get(tool)
    if real is None:
        raise KeyError("no descriptor for %r" % tool)
    worse = descriptor or dict(real, failure="Returns null.",
                               when="When you need it.",
                               purpose="Look something up.")
    tools.DESCRIPTORS[tool] = worse
    try:
        yield
    finally:
        tools.DESCRIPTORS[tool] = real


_DELETIONS = {
    "dedup": _delete_dedup,
    "step_cap": _delete_step_cap,
    "budget_ceiling": _delete_budget,
    "fat_observation": _fatten_observation,
    "weak_descriptor": _weaken_descriptor,
}


def available():
    return sorted(_DELETIONS)


# ---------------------------------------------------------------------
# making the failure observable
# ---------------------------------------------------------------------
def looping_script(case_id, repeats=2):
    """The working script with one turn repeated.

    The deletion lets the loop CONTINUE; this is what makes it go round.
    A model that has forgotten it already asked is the behaviour; the
    missing guard is why nothing stops it.
    """
    from D4_eval_set import scripts
    steps = copy.deepcopy(scripts.SCRIPTS[case_id])
    repeat = copy.deepcopy(steps[1])
    repeat["thought"] = "Let me check that again to be sure."
    return steps[:2] + [repeat] * repeats + steps[2:]


@contextlib.contextmanager
def scripted_as(case_id, steps):
    from D4_eval_set import scripts
    original = scripts.SCRIPTS[case_id]
    scripts.SCRIPTS[case_id] = steps
    try:
        yield
    finally:
        scripts.SCRIPTS[case_id] = original


def verify_restored(case_id, name, problem="A", **options):
    """Putting X back must recover the behaviour. Returns (bool, detail)."""
    from D1_agent_loop.agent import run_case
    before = run_case(case_id, problem=problem)
    with deletion(name, **options):
        pass
    after = run_case(case_id, problem=problem)
    drop = ("seconds",)
    a = {k: v for k, v in before.items() if k not in drop}
    b = {k: v for k, v in after.items() if k not in drop}
    if a == b:
        return True, "identical before and after the deletion was reversed"
    return False, "still differs on: %s" % sorted(
        k for k in a if a.get(k) != b.get(k))
