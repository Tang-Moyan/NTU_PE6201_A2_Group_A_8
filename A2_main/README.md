# A2_main · Problem A submission

PE6201 Assignment 2 — **Problem A** (health-insurance claim first response).  
**Team A-8** · Repository: https://github.com/Tang-Moyan/NTU_PE6201_A2_Group_A_8.git

**This folder is the full submission.** It contains the agent, tool layer, guardrails, harness, backends, fixtures, measurements, and report assembly. Everything needed to mark and reproduce the work lives under `A2_main/` — including `data/` (fixtures + answer key) and `output/` (measured JSON).

---

## Commands a marker should run

All paths below are from the **repository root** (the directory that contains `A2_main/`).

```bash
# Reproducible scripted eval (no key, no network) — D5(a) / Technical Execution
python A2_main/run_eval.py

# Full offline measurement suite (scripted; writes A2_main/output/*.json)
python A2_main/run_all.py

# Deliverable self-checks (should be green on a complete submission)
python A2_main/test_all.py

# Assemble the six-section report from answers + measured JSON
python A2_main/report/assemble.py
```

Optional:

```bash
python A2_main/data/check_my_data.py               # fixture integrity (shipped rows fingerprinted)
python A2_main/D5_model_battery/battery.py         # D5(a) scripted battery (free)
python A2_main/D5_model_battery/merge_battery.py   # merge per-owner D5 live shards
```

**Live battery (costs money)** — only if you need to re-run a model:

```bash
# PowerShell example
$env:A2_LIVE="1"
$env:A2_OWNER="Moyan"          # must match answers_D5.MODELS owner
$env:OPENROUTER_API_KEY="..."
python A2_main/D5_model_battery/battery.py
```

Default `BACKEND` in committed `config.py` is **`scripted`**. Live results already live in `A2_main/output/D5_battery_*.json` and the merged `D5_battery.json`.

---

## What lives where

```
A2_main/
├── run_eval.py                 Marker entry (scripted)
├── config.py                   BACKEND / MODEL / BASE_URL + caps (D5 / D3)
├── data/                       Fixtures, answer key, generators, check_my_data
├── CONTRIBUTIONS.md            Who owned what
├── results.json                Eval artefact for the report
│
├── D0_why_an_agent/            Ladder, good-run statements, s = P^(1/T)
├── D1_agent_loop/              ★ ReAct loop (agent.py)
├── D2_tool_layer/              ★ Tools, descriptors, prompt, parallel / descriptor A-B
├── D3_guardrails/              ★ Caps, dedup, gate, 10-case checklist
├── D4_eval_set/                ★ Harness, scripts, eval runner
├── D5_model_battery/           ★ Scripted + live backends, battery, merge
├── D6_cost_model/              Three layers, four levers, break-even
├── D7_failures/                Two deletion-style failure reproductions
├── report/                     Six-section assemble + prose
├── common/                     Shared helpers, store, TEMPLATE sentinel
└── output/                     All measured JSON (pass rates, costs, batteries)
```

★ = core implementation a marker may want to open first.

Each `Dx_*/` folder typically has:

| File | Purpose |
|---|---|
| `WORKPLAN.md` | What that deliverable asked for |
| `answers_Dx.py` | Decisions and prose that feed the report |
| implementation `.py` | Code under test |
| `test_Dx.py` | Consistency / progress checks |

---

## How numbers flow between deliverables

Measurements are written once to `output/*.json` and re-read elsewhere (so the report does not invent three different pass rates by hand).

```
D4 eval_runner   → P, turn distribution  ─┬→ D0 arithmetic, D3 cap defence
D7 failure_runs  → median turns T        ─┘
D2 tool_audit    → lever 1 (tool-block tokens)
D2 parallel_ab   → lever 2 (turns / input tokens)
D2 descriptor_ab → lever 3 (return tokens)
D4 / D5 live     → lever 4 (success rate)
D5 battery       → per-model cost / pass  → D6 break-even
```

`run_all.py` runs in **dependency order**, not alphabetical order. D0 is written early but measured last, because `s = P^(1/T)` needs the harness numbers.

---

## `test_all.py` exit codes

| Code | Meaning |
|---|---|
| `0` | Complete and verified |
| `1` | Nothing broken; soft TODOs remain |
| `2` | Contradiction / FAIL (e.g. caps in answers ≠ `config.py`) |

On a finished submission, expect **`0`**.

---

## Headline measured results (already in `output/`)

| Finding | Figure | Source |
|---|---|---|
| Scripted eval | 100% over 81 trials / 45 cases, median 3 turns | `D4_eval.json` / D5 scripted |
| Live battery (merged) | glm-5.3 77.8%, grok 72.8%, gemini 50.6%, luna 42.0%, gpt-4o-mini 33.3% | `D5_battery.json` |
| Parallel vs sequential (CLM-8842) | 4 turns / 21k tokens vs 7 turns / 48k | `D2_parallel.json` |
| Descriptor rewrite (live, same model) | v1 43.2% → v2 50.6%; returns ~296 → ~21 tokens | `D2_descriptor.json` + Keerthi/Jojo shards |
| Break-even (cheap vs mid) | ~50.5%; cheap measured 33.3% | `D6_cost.json` |
| Vendor neutrality | Single network site: `backends.py` `_vendor_http` | `test_D5.py` |

These are **measurements**, not estimates (except where a file explicitly marks `estimated`).

---

## Fixtures rule

`A2_main/data/check_my_data.py` fingerprints every **shipped** fixture row under `A2_main/data/data_A/`.

- **Do not edit or delete shipped rows.**
- New cases use **new ids** only.

```bash
python A2_main/data/check_my_data.py
```

---

## Report and other artefacts

```bash
python A2_main/report/assemble.py
```

Prose lives in `report/answers_report.py`. Contribution table: `CONTRIBUTIONS.md`.  
Self-appraisal sheet: `TEAM_SELF_APPRAISAL.md` (required with the zip; not graded).

Submit as `PE6201_A2_A-8.zip` plus the demo video link recorded in `answers_report.VIDEO_URL`.
