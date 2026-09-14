# D2 · The tool layer — what to do

> **This is the layer that decides whether the agent is any good.**
> Class 4 calls the tool layer the ACI (Agent–Computer Interface) and
> points out: **the tool descriptions and signatures are the entire
> instruction manual the model gets** — it cannot ask a colleague, hover
> a tooltip, read your source, or try something in staging. Everything
> in D2 follows from that sentence.
>
> Report section 2 is 450 words, the largest of the six sections.

---

## What is in this folder

| File | What it is | Do you edit it? |
|---|---|---|
| `answers_D2.py` | **User work file**; all three parts live here | **Yes** |
| `tool_audit.py` | D2(a): three-question score table + tool-block token measure | No |
| `descriptor_ab.py` | D2(b): v1 vs v2 measurement | No |
| `parallel_ab.py` | D2(c): serial vs parallel measurement | No |
| `test_D2.py` | All checks + both experiments | No |

```bash
python A2_main/D2_tool_layer/test_D2.py          # full check
python A2_main/D2_tool_layer/tool_audit.py       # D2(a) report
python A2_main/D2_tool_layer/descriptor_ab.py    # D2(b) report
python A2_main/D2_tool_layer/parallel_ab.py      # D2(c) report
```

---

## D2(c) already has a strong finding — look at it first

`parallel_ab.py` has already measured this on the current scaffold.
**You do not need to fill anything in first:**

| | turns | input tokens | result |
|---|---|---|---|
| Serial (one call per turn) | 8 | 59,400 | **escalate — wrong** |
| Parallel (scaffold as-is) | 4 | 21,000 | approve_in_principle |

**The serial branch is not merely more expensive — it hit the 60,000
budget ceiling, was stopped by a guardrail, and returned the wrong
conclusion.**

That is the strongest argument D2(c) can make: packing independent
calls is not a "token-saving neatness" issue. On this evidence it is
whether **this run can stay inside the budget**. Cite both numbers
together in report section 2.

> Why this happens: the loop is stateless; the whole trajectory is
> re-sent every turn. Serial spreads 8 calls over 8 turns, so history
> is re-sent 8 times instead of 4, and growth is quadratic:
> `input ≈ B×T + D×T(T-1)/2`.

---

## What D2(a) asks you to write: tools are chosen

One row per tool in `TOOL_AUDIT`, three questions. **All seven tools
must be present**; `test_D2.py` checks.

### What a good answer to each question looks like

| Question | Shape of a good answer |
|---|---|
| 1 · Without it, which task actually fails? | **Name that task**. Start from the minimum set; add only for **observed** failures, never **imagined** ones |
| 2 · Will the model confuse it with a neighbour? | The driver is **distinguishability**, not count. Ten clearly different tools are fine; three overlapping ones are trouble. **If you cannot say in one sentence when to use A rather than B, the model cannot either** |
| 3 · Cost when it is never called? | It lives in the prompt prefix, **re-sent and re-billed every turn**; it enlarges the failure surface you cannot exhaustively test; if it writes, it needs a gate |

### Find your search_notes

Of Class 4's own five tools, `search_notes` **fails both question 1 and
question 2** ("nothing fails without it" + "it is confusable"), and it
**is also the tool that wrecked the agent**. That is not a coincidence;
that is the argument.

`tool_audit.py` will flag any of your tools with the same signature.
First think hard about this one: does `lookup_hospital` actually pass
question 1? Panel status does not change the outcome; it only changes
what the record must **say**.

### Cutting a tool is explicit extra credit

> *"A tool you removed, naming the observation that removed it, earns explicit credit —
> that is the behaviour nobody does naturally."*

Each item in `TOOLS_CUT` must name three things: the tool, why it was
added, and **which observation made you delete it**. The last one is
the key — not "we felt it was unused", but "on case X we observed Y".

Before adding a tool, try not adding one. Four moves in priority order
(`FOUR_MOVES_TRIED`):

1. Widen an existing tool's arguments instead of adding a sibling
2. Return more from one call instead of adding a second lookup
3. Move this step out of the loop into ordinary code
4. Only then add a tool

**Rubric: four justified tools beat eleven.**

---

## What D2(b) asks you to write: descriptors and the measured rewrite

### Six-field descriptors

All seven tools already have them in `D2_tool_layer/tools.py::DESCRIPTORS`.
`test_D2.py` checks that every callable tool has a descriptor and all
six fields — **a tool the model can call but was never told about is
the kind of bug that costs you an evening**.

### At least two poka-yoke

The key requirement: say what it makes **impossible**, not what it
**discourages**. `test_D2.py` will fail you if your wording contains
"discourage" / "remind" / "should not" and similar.

One already in the scaffold: `check_coverage` requires `policy_id`, so
"look up coverage against no policy and get a confident answer about
nothing" **cannot happen**.

You can copy the Class 4 table format:

| Before | After | What it makes impossible |
|---|---|---|
| `site: str` | `site: Literal["SIN-DC1","KUL-DC2"]` | A mistyped site silently returning "no record" |
| `patient_name` | `patient_id` | Finding the wrong "Mr Chen" |
| `send_email(...)` | `draft_email(...)` + `send_email(...)` | Meaning to draft and sending |
| `dry_run: bool` | `dry_run: bool = True` | The default sitting on the irreversible side |

### The measured rewrite — three of the four numbers are free

D2(b) wants three numbers: **tokens returned per call · evaluation pass
rate · guardrail cases passed**.

| What to measure | Can scripted measure it? | Why |
|---|---|---|
| Descriptor / prompt size | Yes — exact, free, offline | It is string length |
| Tokens returned per call | Yes — exact, free, offline | Return shape is **our code**, not the model's |
| Guardrail cases passed | Yes — free | Guardrails are code; the model has no say in whether they fire |
| Evaluation pass rate | No — **must be live** | The scripted backend replays actions we wrote; **it never consults the model, so it never reads the prompt** |

That last row matters: reporting an "unchanged pass rate" under scripted
as evidence is theatre. That number has to come from D5's live battery —
**the same fixed model**, one run on v1, one run on v2.

**Suggested experiment tool: `get_preauthorisation`.** Its `failure`
field carries the costliest misread in the assignment: `None` is not
the same as not covered; it means "evidence missing", which maps to
**request**, not a denial. Degrade v1's failure to `"Returns null."`
(Class 4 says that is what teams write most often) and the contrast is
sharp.

`v1_return()` is the only place here where you **write code** rather
than fill a blank. The function is at the bottom of `answers_D2.py`;
the docstring has an example.

### The sentence that belongs in the report

> A prompt instruction is paid **on every call, every run, forever**,
> and **dies when you change models**; an interface constraint is
> **paid once and holds permanently**.

Honesty requirement: if v2 is neither smaller nor safer, **say so**.
An honestly reported rewrite that did not help scores higher than one
that was never measured.

---

## What D2(c) asks you to write: the dependency rule

There is only one criterion: **a pair of tools may share a turn if and
only if neither needs the other's output.**

Ready-made structure for Problem A:

```
turn 1   get_claim                              must run alone — everything
                                                later needs its return
turn 2   lookup_policy
       + check_coverage × n (once per line)     mutually independent
       + lookup_hospital
turn 3   get_preauthorisation                   cannot join turn 2:
                                                until coverage answers,
                                                you do not know which
                                                line needs it
turn 4   issue_decision_letter                  gated, but still a
                                                normal turn
```

Once `DEPENDS_ON` is filled, `parallel_ab.py` **uses it to validate
your scripts** — if a turn places A together with a B that A depends
on, it will report it. **A rule nobody executes is documentation; this
one is executed.**

### Two honest limits (required, and "we expect you to find them")

1. **When parallel is more expensive**: in serial, an early observation
   can tell you to skip a later call. `CLM-8925` finds the annual-limit
   breach at turn 2 and exits early — if you fire all four coverage
   checks in parallel, those four are wasted.
2. **It removes a decision point**: the model could otherwise change
   its mind at the middle step. Say where your dependency rule draws
   the line, and why.

---

## Suggested structure for report section 2 (450 words)

| Para | Content | Words |
|---|---|---|
| 1 | Why this tool set: one-sentence conclusion from the three questions + shortest defensible list | 90 |
| 2 | What we cut, and which observation made us cut it | 80 |
| 3 | Two poka-yoke, each in one sentence of "what it makes impossible" | 60 |
| 4 | What the descriptor rewrite measured: three numbers + the "prompt paid forever / interface paid once" sentence | 100 |
| 5 | Dependency rule + the two parallel-saving numbers + **the finding that serial hit the budget ceiling** | 90 |
| 6 | Two honest limits | 30 |

Put the tables in the repo: three-question score table, poka-yoke
table, v1/v2 comparison, serial vs parallel. The tables printed by
`tool_audit.py` and `parallel_ab.py` can be used as-is.
