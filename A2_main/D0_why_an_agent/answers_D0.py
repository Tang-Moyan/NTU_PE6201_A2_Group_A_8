"""
D0 - USER WORK FILE  ("Why an agent at all")
=====================================================================
本文件是 D0 唯一需要你们填写的地方。框架代码 (framework.py /
reliability.py) 只读取这里，不需要你们改动。

填写规则
  - 把整个 TEMPLATE(...) 调用替换成你的答案，不要保留 TEMPLATE 外壳。
  - 值一律用英文写：这些字符串会直接进入报告第 1 节，评分人读英文。
  - hint 是中文，只是给你们看的指引，不会进报告。

进度自查：  python A2_main/D0_why_an_agent/test_D0.py

顺序提醒：D0(c) 的五条标准必须在写第一行 agent 代码之前提交
(committed)，评分人会看 commit history。先填 GOOD_RUN_STATEMENTS 并
单独 commit 一次。
=====================================================================
"""
from common.template import TEMPLATE

# =====================================================================
# D0(a) - 把问题放到 Class 4 的梯子上，并为这一级辩护
# =====================================================================

RUNG = 7

RUNG_DEFENCE = (
    "Our health-insurance claim first-response problem belongs on Rung 7 because "
    "the number of claim lines is not known until get_claim returns, and each "
    "procedure's requires_preauth flag determines at runtime whether an additional "
    "pre-authorisation lookup is needed. The sequence and number of tool calls therefore "
    "depend on the record observed during execution rather than being fixed in advance."
)

# 报告第 1 节要求："什么是 rung 1-6 能给的，什么是不能给的"
# 每一级都要有一句话，说明它在这个问题上会在哪里失效。
RUNG_COUNTERFACTUAL = {
    1: (
        "A single call is insufficient because the system must retrieve and verify "
        "multiple records that are not all known before the claim is inspected."
    ),
    2: (
        "A fixed prompt chain is insufficient because the required sequence changes "
        "with the claim; it would either skip conditional evidence or waste calls on "
        "cases that should terminate early."
    ),
    3: (
        "Routing can send claims into different lanes, but each lane still contains "
        "variable line-item, coverage, and pre-authorisation paths that cannot be fixed "
        "in advance."
    ),
    4: (
        "Parallelisation can reduce turns by running independent checks together, but "
        "it cannot replace the loop because later checks, such as pre-authorisation, "
        "depend on facts discovered during earlier tool calls."
    ),
    5: (
        "Orchestrator-workers can dynamically delegate subtasks, but delegation alone "
        "does not provide the repeated observation-action loop needed to follow "
        "conditional evidence and decide when the final gated action is justified."
    ),
    6: (
        "Evaluator-optimiser can critique or improve an existing answer, but it cannot "
        "by itself discover missing business facts unless the system can choose and "
        "re-call tools based on new observations."
    ),
}

# ---------------------------------------------------------------------
# 1 · The workflow test - 四个问题
#     第二行是决定性的：步骤数是否随输入变化。
# ---------------------------------------------------------------------
WORKFLOW_TEST = {
    "who_decides_sequence": (
        "The model decides the next step at runtime from the observations returned "
        "by the tools. Our code defines the available tools, limits, and approval gate."
    ),
    "steps_vary_with_input": "yes",
    "can_you_test_every_path": (
        "No. The number and order of tool calls vary with the claim, so we evaluate "
        "outcomes across a representative case set rather than enumerate every path."
    ),
    "what_does_it_cost": (
        "Cost and latency vary with the path taken and are only predictable after "
        "applying explicit turn and token caps."
    ),
}
# 证据：用你们自己评估集里的具体 case 证明步骤数确实变化。
# 至少两个 case，一短一长，写出 case_id + turn 数 + 为什么不同。
# 提示：test_D0.py 会自动去 output/D4_eval.json 读实测 turn 分布，
#       你只需要在这里写出解释。
STEP_VARIATION_EVIDENCE = (
    "CLM-8925 stops at 2 turns: the annual limit is already breached, so "
    "line-level pricing would be turns spent on a decision it was never "
    "going to make. CLM-8850 resolves in 3 turns (one covered line, no "
    "pre-authorisation). CLM-8960 takes 4 turns (four lines, four coverage "
    "checks folded into one turn, then the gated letter). The measured "
    "histogram on 81 trials is turns 2 / 3 / 4 — the step count varies "
    "with the claim, not with a fixed workflow."
)

# ---------------------------------------------------------------------
# 2 · The two conditions - 缺一不可
# ---------------------------------------------------------------------
CONDITION_STEPS_UNKNOWN = (
    "The required steps are not known in advance because each claim can contain "
    "a different number of lines, and requires_preauth is discovered at runtime "
    "for each procedure."
)

CONDITION_GROUND_TRUTH_EACH_STEP = (
    "Each turn ends with a tool observation retrieved from the fixture records. "
    "The next action is therefore corrected by external record evidence rather "
    "than by the model's own previous statement."
)

# ---------------------------------------------------------------------
# 3 · The three-question test - 治理悬崖在哪
#     retrieval -> agentic retrieval 不是悬崖；
#     agentic retrieval -> agent（第一次写）才是。
# ---------------------------------------------------------------------
FIRST_IRREVERSIBLE_ACTION = "issue_decision_letter"

IRREVERSIBLE_ACTION_WHY = (
    "Once a member has been told that a claim is approved in principle, reversing "
    "that communication can create a complaint and operational consequences rather "
    "than being a harmless edit. The preceding retrieval tools can be re-run without "
    "changing the external state."
)

GOVERNANCE_CLIFF = (
    "Before issue_decision_letter, the loop is agentic retrieval because the tools "
    "are read-only. The first write turns the system into an actor, so that action "
    "is placed behind a confirmation gate."
)


# =====================================================================
# D0(b) - 什么时候不该建 agent。两个测试都要诚实回答。
# =====================================================================

# ---------------------------------------------------------------------
# Test 1 · The ground-truth test
#   什么能在几秒内告诉这个 loop 它错了？
#   快且客观 -> 可以建 agent；慢或主观 -> 带人工闸门的 workflow。
# ---------------------------------------------------------------------
# 每一项：records = 哪张系统记录表，answers_in = 多快，objective = 是否客观
GROUND_TRUTH_SOURCES = [
    {
        "record": "policies.json status and coverage dates",
        "answers_in": "milliseconds - a local record lookup",
        "objective": "yes - policy status and effective dates are stored facts",
    },
    {
        "record": "preauthorisations.json validity windows",
        "answers_in": "milliseconds - a local record lookup",
        "objective": "yes - the authorisation reference and validity dates are stored facts",
    },
    {
        "record": "decided_claims.json prior claim records",
        "answers_in": "milliseconds - a local record lookup",
        "objective": "yes - duplicate evidence can be checked against recorded claim facts",
    },
]

GROUND_TRUTH_VERDICT = (
    "The main record checks return objective ground truth in milliseconds, so the "
    "retrieval loop can proceed autonomously. Judging whether member-supplied narrative "
    "contains an instruction is less objective, which is why the irreversible write "
    "remains behind a confirmation gate."
)
# ---------------------------------------------------------------------
# Test 2 · The arithmetic
#   P 和 T 由框架从 D4 / D7 的实测结果自动读取并算出 s = P^(1/T)。
#   你们要填的是"这个数说明了什么"。
# ---------------------------------------------------------------------
ARITHMETIC_READING = (
    "Step count. On the scripted set implied s is already high (near 1.0) "
    "while the median run is still 3 turns and the longest legitimate run "
    "is 4; the D2(c) serial arm on CLM-8842 burned 8 turns / 59,400 tokens "
    "and hit the budget ceiling. Cutting T by packing independent coverage "
    "checks moves pass rate and cost more than any descriptor polish we "
    "have measured so far."
)

WEAK_STEP_READING = (
    "The framework flags check_coverage as the candidate weak step. We "
    "took move (a): a tighter return shape (required_document folded into "
    "the same call; policy_id required so coverage against no policy is "
    "impossible) rather than removing the tool. A fat or ambiguous "
    "coverage observation both lowers s and raises T, because the agent "
    "re-reads and re-asks; fixing the return attacks both."
)

ARITHMETIC_LIMITS = (
    "The arithmetic assumes steps are independent and similarly reliable, but this "
    "does not fully hold in practice: one poor early observation can cause later "
    "errors, and different tools have different failure rates. We therefore use s "
    "as a diagnostic for distinguishing step quality from step count, not as a "
    "physical constant of the system."
)


# =====================================================================
# D0(c) - What good looks like
#   五条编号陈述，必须在第一个 agent commit 之前提交。
#   D4 的评估集是这份清单的下游：如果某一条不可测，就重写到可测为止。
#   第 4 条（说"我不知道"而不是编造）是团队最常漏的，也是 negative
#   case 存在的理由。
# =====================================================================
GOOD_RUN_STATEMENTS = [
    "1. Names the actual cause of the claim outcome and ties it to evidence from the system records.",
    "2. Produces a decision consistent with the policy, coverage, pre-authorisation, document, and claim records.",
    "3. Takes the gated external action at most once and only after the required facts have been established.",
    "4. When the records cannot support a decision, escalates or requests "
    "missing evidence rather than inventing an answer it does not know.",
    "5. Reaches the correct outcome with fewer unnecessary tool calls while preserving the same safety and evidence requirements.",
]

# 每一条对应哪些 case 来验证它。写 case_id 列表，D4 会检查这些 case 存在。
GOOD_RUN_TESTABILITY = {
    1: ["CLM-8933", "CLM-8894"],
    2: ["CLM-8842", "CLM-8960"],
    3: ["CLM-8842", "CLM-8850"],
    4: ["CLM-8888", "CLM-8941"],
    5: "Verified with the D6 cost model and measured turn counts rather than a single claim case.",
}
