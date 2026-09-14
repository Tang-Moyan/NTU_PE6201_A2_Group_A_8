# D7 · Two reproduced failures — what to do

> Reproduce two **different** failure modes, each fixed **at the layer
> where the fix belongs**.
>
> **Shape rule (the most important one)**: each failure must be built as
> **"your working agent, minus X"**, not as a separately written bad
> agent. **Putting X back must recover the original behaviour.** That is
> the difference between a diagnosis and a story.
>
> **"For both failures, state which layer the fix belongs in and why the other two
> were the wrong place. That judgement is most of the mark."**

---

## What is in this folder

| File | What it is | Do you edit it? |
|---|---|---|
| `answers_D7.py` | **User work file**: both failure definitions + three-layer argument | **Yes** |
| `deletion.py` | Five available deletions, all context managers, auto-restore | Maybe add |
| `failure_runs.py` | Before/after comparison + turn distribution; produces report section 5 | No |
| `test_D7.py` | Checks that the failure **shape** is valid | No |

```bash
python A2_main/D7_failures/test_D7.py
python A2_main/D7_failures/failure_runs.py    # full report section 5
```

---

## Five deletions already available

| Name | Layer | What it deletes |
|---|---|---|
| `dedup` | code | Action de-duplication (**use this for Failure 1**) |
| `step_cap` | code | Turn cap |
| `budget_ceiling` | code | Token cap |
| `fat_observation` | **tool interface** | A tool's return filter — falls back to the whole table |
| `weak_descriptor` | **prompt** | Swap a descriptor for a deliberately worse version |

`test_D7.py` has already verified that **all five restore cleanly**.
You may also add your own in `deletion.py`, as long as it is "delete
one thing" rather than "write a bad agent".

---

## Failure 1 · loop control — required, and already measured

You can see the result now:

| | turns | tool calls | tokens | decision |
|---|---|---|---|---|
| before | 4 | 8 | 21,600 | `approve_in_principle` |
| after (dedup deleted) | 6 | 18 | 38,640 | `approve_in_principle` |

### Watch the **result**, not the process

After the guard is deleted:

- **The run does not crash.** No exception, no error
- It repeats a call it has already made, burning turns and tokens
- **And still returns the correct answer**
- **A pass-rate table will show it as a clean pass**
- The step cap and the budget ceiling **do not fire**, because neither
  was breached

> **They bound the damage; they do not detect the fault.**

That is why instrumentation is a **requirement**, not a nicety:
**you cannot report a failure you had no way to notice.**

### Four things to report

| # | What to report | Who gives it to you |
|---|---|---|
| 1 | Which instrumentation found it | `failure_runs.py` prints it |
| 2 | Turn distribution on **the whole eval set**: median, worst, how often the cap was hit | Automatic, including a histogram |
| 3 | Which layer the fix is in, **and why the other two were the wrong place** | You write this in `answers_D7.py` |
| 4 | Before/after: turns / tokens / cost **/ pass rate** | Automatic |

The **pass rate** in item 4 is easy to miss:
**a cap that stops a runaway run will also truncate a legitimate long
run** — that is trading one failure for another. Check this on **the
whole set**, not one case.

### How to write the three-layer argument

| Layer | Why it is not this one |
|---|---|
| tool interface | No return shape can stop a caller asking the same question twice |
| prompt | **The thing that forgot is the model itself. Only the code layer remembers.** |
| code (this is it) | But say **which** mechanism inside the code layer: the step cap and the budget ceiling did not fire; only de-duplication detected the fault **and named the reason** |

---

## Failure 2 · must be a different layer

**Not loop control again.** It must be **tool interface** or **prompt**.
`test_D7.py` checks this and fails immediately if you pick the code
layer.

Class 4's worked example is at the **tool interface**: a fat, stale
observation carrying a landmine — 246 tokens, producing a confident
wrong answer, **fixed at the interface, not by adding a sentence to the
prompt**.

`fat_observation` is that shape: make `check_coverage` return the whole
procedures + policies tables, so observation size per call goes from
about 30 tokens to about 900 — **and every one of those is re-sent on
every later turn**.

### The sentence that belongs in the report (Class 4 Section 7)

> A prompt instruction is paid **on every call, every run, forever**,
> and **dies when you change models**; an interface constraint is
> **paid once and holds permanently**.

### If you choose `weak_descriptor` (prompt layer)

Note: **it only bites on a live backend.**
The scripted backend never consults the model, so it never reads the
prompt. Offline you can measure prompt size; behavioural impact needs
D5's battery. **Say in the report which of those you are reporting.**

---

## Caps must come from evidence

`failure_runs.py` prints: median, worst legitimate, cap-hit count, and
a histogram.

> *"If your median run is 4 turns and your worst legitimate run is 7,
> a step cap of 8 is defensible and a step cap of 30 is decoration."*

`CAP_JUSTIFICATION` must put those three numbers in one sentence.
`test_D7.py` will warn you if the cap sits far above the longest
legitimate run you have observed.

**Order reminder**: run `failure_runs.py` first to get the distribution,
then go back to D3 to fill `LIMITS`, then to D6 to fill `CAPS`. The
three must agree; `test_D3.py` and `test_D6.py` both check.

---

## Suggested structure for report section 5 (250 words)

**This section is deliberately short. Two tight failures are more
convincing than two sprawling narratives.**

| Para | Content | Words |
|---|---|---|
| 1 | Failure 1: what was deleted, the four before/after numbers, **"it did not crash, the answer was still right, a pass-rate table would not show it"** | 90 |
| 2 | Failure 1 layer argument: why code, why the other two layers will not do | 50 |
| 3 | Failure 2: what was deleted, which instrumentation found it, before/after numbers | 60 |
| 4 | Failure 2 layer argument + the "prompt paid forever / interface paid once" sentence | 50 |

Put the turn-distribution histogram and the before/after table in the
repo.
