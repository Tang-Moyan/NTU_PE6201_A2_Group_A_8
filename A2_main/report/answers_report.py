"""
REPORT - USER WORK FILE  (the prose that belongs to no single D)
=====================================================================
报告六节、最多 2000 词。**表格和图不计入，只有正文计。**

大部分内容来自各个 D 的 answers 文件。这里只放**不属于任何单个 D**
的那些：第 6 节的整体反思，以及每一节的最终定稿正文。

工作方式建议：
  1. 先跑 assemble.py 看各节的**素材**（各 D 的答案 + 实测数字）
  2. 根据素材写定稿正文，填进下面的 SECTION_*_PROSE
  3. 再跑 assemble.py，它会统计字数并告诉你哪一节超预算

进度自查：  python A2_main/report/assemble.py
=====================================================================
"""

# =====================================================================
# 提交信息
# =====================================================================
TEAM_ID = "A-8"
PROBLEM_CHOSEN = "A"          # 这个仓库已经只做 Problem A，不用改

REPO_URL = "https://github.com/Tang-Moyan/NTU_PE6201_A2_Group_A_8.git"

VIDEO_URL = (
    "PENDING: replace with the public 5-minute demo URL before NTULearn "
    "submit (system running, one negative case live, every member speaks)."
)


# =====================================================================
# 第 6 节 · What we would not deploy  (150 词)
# =====================================================================
LIMITS_WE_FOUND = (
    "Three limits showed up in measurement. First, scripted 100% does not "
    "transfer: the same 45 cases drop to 33–78% live, so a marker who only "
    "reads the scripted table overstates readiness. Second, injection "
    "detection is still brittle - every live model scored near 0% on the "
    "three prompt_injection families, including glm-5.3. Third, "
    "auto-grading on trigger strings fails honest escalations that use "
    "near-synonyms (e.g. instruction_in_narrative vs "
    "instruction_in_member_narrative), so code_check under-counts quality."
)

WOULD_NOT_DEPLOY = (
    "Not at autonomy='act', and not on the cheap model: gpt-4o-mini is "
    "17 points below the 50.5% break-even while one escalation costs "
    "US$7.60, and our narrative/injection check is the one input we "
    "cannot verify against a fixture record."
)


# =====================================================================
# 各节定稿正文
# =====================================================================
SECTION_1_PROSE = """Rungs 1–6 are insufficient for this health-insurance claims workflow because improving an individual model response does not guarantee a correct, bounded, end-to-end decision. A real claim requires the system to retrieve documents, confirm policy status, apply coverage rules and exclusions, calculate the payable amount, and choose whether to approve, deny, or escalate. Each transition depends on earlier evidence and must remain auditable. A larger model, longer prompt, fixed chain, retrieval, or tool access in isolation does not provide the planning, state tracking, evidence checks, bounded retries, and human gate needed when evidence is missing, contradictory, stale, or hostile. The D2 comparison makes this operational: for case CLM-8842, the serial design took eight turns and 59,400 input tokens and stopped at the 60,480-token budget, whereas parallel calls completed in four turns with 21,000 input tokens. The problem is therefore orchestration and control, not simply model capability.

On the scripted evaluation, the end-to-end pass rate was P = 1.000 across a three-step decision path (T = 3). Under the simplifying assumption that steps are independent and equally reliable, P = s^T, so the implied per-step reliability is s = P^(1/T) = 1.000^(1/3) = 1.000. This is an exact 1.0 on the scripted set, not a production guarantee. All 81 scripted trials passed the code check, but the fixed backend and absence of observed failures do not measure distribution shift, ambiguous evidence, tool outages, or new prompt-injection wording. Reliability also compounds quickly: if each of six steps were 0.98 reliable, end-to-end reliability would be only 0.98^6 = 0.886. An agent is justified only when its autonomy is surrounded by measurable controls.

We therefore define a good run using five observable statements:
(1) It retrieves the correct claim and policy records and relies only on current, authoritative evidence.
(2) It selects the necessary tools, parallelises independent calls, and avoids duplicate or irrelevant work.
(3) It remains within turn, token, and cost limits, stopping with an explicit, auditable reason if a limit or dependency fails.
(4) It treats claimant and provider text as untrusted, resists prompt injection, and never allows external text to alter system rules or trigger an irreversible action.
(5) It produces a consistent approve, deny, or escalate decision with supporting evidence, a checked calculation, recorded uncertainty, and human review before payment or final rejection."""

SECTION_2_PROSE = """The tool set is chosen, not accumulated. Six tools remain after cutting lookup_hospital: get_claim, lookup_policy, check_coverage, get_preauthorisation, check_duplicate_claim, and gated issue_decision_letter. Panel status now rides on get_claim's hospital object; CLM-8874 still expects approve_in_principle for a non-panel hospital, so a dedicated lookup never earned a turn. Each kept tool fails a real task without it, is distinguishable from its neighbours, and pays a prompt-prefix cost even when unused.

Descriptors are six-field contracts. The measured rewrite is get_preauthorisation. v1 returned the whole table (~296 tokens per call) behind a short descriptor; v2 returns a five-field projection (~21 tokens) behind a longer, explicit failure field that separates never-requested from expired. Descriptor cost rose by 138 tokens once per turn; observation cost fell ~93% and compounds on later turns. Guardrails stayed 10/10 because they do not read descriptors. Live, on the same gemini commit, v1 scored 43.2% and v2 50.6% (preauth families 11.8% to 29.4%) - so the interface change moved accuracy where the theory predicts, which a scripted backend cannot show.

Multi-call turns follow one dependency rule: share a turn only when neither call needs the other's output. get_claim alone; then policy, duplicate and per-line coverage together; get_preauthorisation only after coverage names which line needs it; the letter last and gated. On CLM-8842 that packing cut 7 turns / 48,000 input tokens to 4 / 21,000 (~43% turns, ~56% tokens) without changing the decision. The sequential arm also breached the 60,000-token ceiling - so the saving is both cheaper and more correct under our caps. Unnecessary parallelism still has a cost: on annual-limit cases, early escalate should skip unused coverage calls. We therefore batch only within a dependency level, never across one."""

SECTION_3_PROSE = """We evaluated 45 labelled health-insurance claims. Ordinary cases ran once and negative cases ran three times, giving 81 scripted trials. All 81 passed the deterministic decision and trigger checks. GPT-5.6-sol then reviewed the first-trial decision records against Appendix A, the fixture evidence and each must_record requirement. All 45 records passed this semantic review. The live battery produced much lower scores. On the merged D5 shards, glm-5.3 reached 77.8%, grok-4.6 72.8%, gemini-3.8-flash 50.6%, luna 42.0%, and gpt-4o-mini 33.3%. Negative-case rates tracked the same order (66.7% down to 33.3%). Divergence concentrated on preauth_expired, partly_payable and duplicates; annual_limit and prompt_injection stayed near zero even for the best model. Several live failures used a correct escalate with a non-canonical trigger string, exposing a prompt-contract weakness beside insurance reasoning.

The evaluation set deliberately varies decision routes: missing documents, absent or expired pre-authorisation, lapsed and out-of-date policies, annual-limit boundaries, non-panel providers, duplicates, exclusions, and three prompt-injection claims. The guardrail checklist complements task-level evaluation. All 10 guardrail cases held: the turn cap, budget ceiling and duplicate-action detection fail loudly with an auditable reason. Autonomy tests show why the gate sits on the irreversible letter: under suggest the letter is held; under act the record shows the gate passed. Hostile-text cases escalate with instruction_in_member_narrative rather than steering the decision. Together, the results support bounded autonomous evidence-gathering with human confirmation before any insurer commitment."""

SECTION_4_PROSE = """We use the Class 5 three-layer model on D5 live measurements. Layer 1 averages 8,891 input and 1,019 output tokens per run at OpenRouter list prices for google/gemini-3.8-flash (US$0.75/US$3.75 per million, verified 2026-09-15) - US$0.0105. Layer 2 is (1 - 0.506) x US$7.60 = US$3.75 using our 50.6% gemini pass rate over 81 trials and Appendix A's US$38/hour assessor for 12 minutes. Layer 2 is ~358x Layer 1. Layer 3 is US$73/month.

At 8,000 claims/month the total is about US$30,182 (US$84 tokens, US$30,025 escalations). Cost per successful task is ~US$3.76. At 50.6% the mid-tier arm is not yet shippable; the model makes that visible.

Four measured levers. (1) Tool block 1,167 to 1,098 tokens by cutting lookup_hospital. (2) Turns 215 to 128 and input tokens 1.29M to 0.62M across 45 cases via parallel independent checks - T is the quadratic term. (3) get_preauthorisation returns 296 to 21 tokens; live gemini v1 43.2% vs v2 50.6%. (4) Success rate 33.3% (gpt-4o-mini) to 77.8% (glm-5.3) on the same harness. Lever 4 dominates: one pass-rate point is worth ~US$608/month.

Break-even: C=US$0.00113, E=US$3.76, F=US$7.60 gives 50.5%. The cheap model measured 33.3% - 17 points short - so token savings are erased by rare extra failures. Caps: 8 turns, 60,000 tokens, and a 200-claim/month policy commitment at provisioning."""

SECTION_5_PROSE = """We reproduce two failures as deletions from the working agent, then put the piece back.

Failure 1 is loop control. Deleting action de-duplication on CLM-8842 raises turns from 4 to 6 and tokens from 21,600 to 38,640 while the decision stays correct and no exception fires - the loop burns money in a circle. The step cap (8) and budget ceiling (60,000) never trip. Restoring the guard recovers the original run. The fix belongs in code: a loop has no memory of its own actions unless you give it one; a prompt cannot be trusted to remember, and no return shape stops a caller asking twice.

Failure 2 is the tool interface. Wrapping check_coverage with the full procedures and policies tables on CLM-8842 leaves pass rate and median turns unchanged on the 81-trial set, but raises cost from US$0.073 to US$0.085 (~16%). The fault is invisible to a pass-rate table and visible only because tokens were counted while the run happened. Caps do not fire (4 turns, ~18.7k tokens). A prompt saying "ignore extra fields" still ships those fields every later turn. Restoring the filtered projection removes the bill permanently.

Across both, the layer judgement is the mark: loop memory is code; observation shape is interface. Caps bound damage after the fact; they do not name these faults. Median 3 and worst legitimate 4 turns justify an 8-turn cap with headroom, not decoration."""

SECTION_6_PROSE = """We would not deploy this system at autonomy=act, or on the cheap live model. gpt-4o-mini sits 17 points below the 50.5% break-even while an escalation costs US$7.60; scripted 100% does not predict live behaviour; and injection families remain near zero even for glm-5.3. The architecture we did not build is a second reviewing agent before the gate. It might have caught fat observations and expired-PA mistakes, but at roughly +40% input tokens per run and a second failure surface across 45 cases. We kept a single agent: D7 Failure 2 was cheaper to fix once at the tool interface than to pay for forever with a reviewer. Confirm stays on issue_decision_letter only."""


# =====================================================================
# 其余三个交付物的自查
# =====================================================================
CONTRIBUTIONS_MD_WRITTEN = True

SELF_APPRAISAL_DONE = True  # fill TEAM_SELF_APPRAISAL and set True before submit

RESULTS_JSON_COMMITTED = True
