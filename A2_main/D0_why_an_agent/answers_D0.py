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

RUNG = TEMPLATE(
    "问题落在第几级？填 1-7 的整数。A2 的两个问题都应落在 7，"
    "但你必须能论证，不能默认。",
    example=7)

RUNG_DEFENCE = TEMPLATE(
    "为什么是这一级？两三句话，必须落到本问题的具体事实上。"
    "关键论据：一个 claim 的 line 数量不固定，requires_preauth 决定"
    "要不要多打一次 preauth 查询——步骤序列在运行前无法枚举。",
    example="A claim carries n line items, and n is not known until "
            "get_claim returns. Each line's requires_preauth flag decides "
            "whether a further lookup happens at all, so the call sequence "
            "is a function of the record, not of our code.")

# 报告第 1 节要求："什么是 rung 1-6 能给的，什么是不能给的"
# 每一级都要有一句话，说明它在这个问题上会在哪里失效。
RUNG_COUNTERFACTUAL = {
    1: TEMPLATE("单次调用为什么不够？", example="One call cannot fetch the policy it has not seen yet."),
    2: TEMPLATE("固定 prompt chain 为什么不够？"),
    3: TEMPLATE("Routing 为什么不够？"),
    4: TEMPLATE("Parallelisation 为什么不够？（注意：我们确实用了并行，但它不是架构，见 D2c）"),
    5: TEMPLATE("Orchestrator-workers 为什么不选？（这是最接近的一级，要认真答）"),
    6: TEMPLATE("Evaluator-optimiser 为什么不选？"),
}

# ---------------------------------------------------------------------
# 1 · The workflow test - 四个问题
#     第二行是决定性的：步骤数是否随输入变化。
# ---------------------------------------------------------------------
WORKFLOW_TEST = {
    "who_decides_sequence": TEMPLATE(
        "谁决定步骤顺序、在什么时候决定？",
        example="The model, at runtime. Our code decides only which tools "
                "exist and where the gate sits."),
    "steps_vary_with_input": TEMPLATE(
        "步骤数是否随输入变化？必须是 'yes' 或 'no'。填 'no' 就说明你该做 "
        "workflow 而不是 agent。",
        example="yes"),
    "can_you_test_every_path": TEMPLATE(
        "能否穷举测试所有路径？",
        example="No. We test outcomes across 40 cases, not paths."),
    "what_does_it_cost": TEMPLATE(
        "成本是否可预测？",
        example="Unpredictable until capped; our step cap is 8 turns."),
}

# 证据：用你们自己评估集里的具体 case 证明步骤数确实变化。
# 至少两个 case，一短一长，写出 case_id + turn 数 + 为什么不同。
# 提示：test_D0.py 会自动去 output/D4_eval.json 读实测 turn 分布，
#       你只需要在这里写出解释。
STEP_VARIATION_EVIDENCE = TEMPLATE(
    "举出至少两个 case_id，说明它们 turn 数不同以及为什么。"
    "shipped 数据里现成的例子：CLM-8850 (单 line，短) vs CLM-8960 "
    "(四 line，长) vs CLM-8925 (超额度，两轮就早退)。",
    example="CLM-8850 resolves in 3 turns (one line, no pre-authorisation). "
            "CLM-8960 takes 4 (four lines, four coverage checks folded into "
            "one turn). CLM-8925 stops at 2: the annual limit was breached, "
            "so pricing the lines would have been turns spent on a decision "
            "it was never going to make.")

# ---------------------------------------------------------------------
# 2 · The two conditions - 缺一不可
# ---------------------------------------------------------------------
CONDITION_STEPS_UNKNOWN = TEMPLATE(
    "条件一：步骤事先未知。用本问题的机制解释，不要复述定义。",
    example="requires_preauth is read at runtime, per line.")

CONDITION_GROUND_TRUTH_EACH_STEP = TEMPLATE(
    "条件二：每一步都拿回 ground truth（工具结果 / 查询 / 跑过的代码），"
    "现实才能纠正它。没有这条就只是一段自洽的独白。",
    example="Every turn ends in a tool observation read from the fixture "
            "JSON, not in the model's own restatement of it.")

# ---------------------------------------------------------------------
# 3 · The three-question test - 治理悬崖在哪
#     retrieval -> agentic retrieval 不是悬崖；
#     agentic retrieval -> agent（第一次写）才是。
# ---------------------------------------------------------------------
FIRST_IRREVERSIBLE_ACTION = TEMPLATE(
    "点名你们的第一个不可逆动作（工具名）。这是问题落在 rung 7 而不是 "
    "5 或 6 的全部理由。",
    example="issue_decision_letter")

IRREVERSIBLE_ACTION_WHY = TEMPLATE(
    "为什么它不可逆？一旦告诉会员 'approved in principle'，收回的代价是什么？",
    example="Once a member has been told a claim is approved in principle, "
            "withdrawing it is a complaint, not an edit. Every other tool in "
            "our set can be re-run harmlessly.")

GOVERNANCE_CLIFF = TEMPLATE(
    "用一句话说清悬崖的位置：在这个写动作之前，系统是 agentic retrieval"
    "（全部只读）；之后它是一个 actor。",
    example="Six of our seven tools are read-only, which makes the loop "
            "agentic retrieval. issue_decision_letter is the one that makes "
            "it an agent, and it is the only one behind a gate.")


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
    {"record": TEMPLATE("系统记录表 1（例：policies.json 的 status/日期）"),
     "answers_in": TEMPLATE("多快？例：'milliseconds - a local row read'"),
     "objective": TEMPLATE("客观还是主观？yes/no + 一句理由")},
    {"record": TEMPLATE("系统记录表 2（例：preauthorisations 的有效期窗口）"),
     "answers_in": TEMPLATE("多快？"),
     "objective": TEMPLATE("客观还是主观？")},
    {"record": TEMPLATE("系统记录表 3（例：decided_claims 的重复判定）"),
     "answers_in": TEMPLATE("多快？"),
     "objective": TEMPLATE("客观还是主观？")},
]

GROUND_TRUTH_VERDICT = TEMPLATE(
    "结论：ground truth 是否够快够客观到允许 loop 无人监督地跑？"
    "注意诚实——narrative 的判断这一步既不快也不客观，这正是我们把 "
    "gate 放在发信之前的理由。",
    example="Three of our four checks answer in milliseconds and cannot be "
            "argued with. The fourth - judging whether a member's narrative "
            "contains an instruction - is neither, which is exactly why the "
            "irreversible step sits behind a confirm gate rather than "
            "running free.")

# ---------------------------------------------------------------------
# Test 2 · The arithmetic
#   P 和 T 由框架从 D4 / D7 的实测结果自动读取并算出 s = P^(1/T)。
#   你们要填的是"这个数说明了什么"。
# ---------------------------------------------------------------------
ARITHMETIC_READING = TEMPLATE(
    "看到实测的 s 之后：你们的问题是 step QUALITY 还是 step COUNT？"
    "二选一并给理由。这决定了接下来该做 D2(b) 还是 D2(c)。",
    example="Step count. Our implied s is high but the median run is long, "
            "and the sensitivity table shows the same s at 3 turns instead "
            "of 6 would move the run pass rate by more than any descriptor "
            "rewrite we attempted.")

WEAK_STEP_READING = TEMPLATE(
    "框架会按'失败前最后一个工具调用'给出候选弱步骤。写出你们的判断："
    "哪个步骤是弱的，以及你们选了 (a) 修它 还是 (b) 去掉它。"
    "注意：弱步骤通常两头都吃亏——返回得差，agent 就会重读、重试、"
    "游走，于是 s 降低而 T 升高。一个修复能同时动两项。",
    example="check_coverage on a narrative-heavy claim preceded most of our "
            "wrong outcomes. We took move (a): a tighter return shape.")

ARITHMETIC_LIMITS = TEMPLATE(
    "说明这个模型的局限（必答，评分点）：步骤不独立——早期一个坏观察会让"
    "后面更糟，而不是同等概率成功；各步骤失败率也不同。所以 s 是诊断"
    "工具，不是系统的物理常数。",
    example="Steps are not independent and not equally failure-prone, so we "
            "read s as a diagnostic - 'quality or count?' - rather than as a "
            "property of the system.")


# =====================================================================
# D0(c) - What good looks like
#   五条编号陈述，必须在第一个 agent commit 之前提交。
#   D4 的评估集是这份清单的下游：如果某一条不可测，就重写到可测为止。
#   第 4 条（说"我不知道"而不是编造）是团队最常漏的，也是 negative
#   case 存在的理由。
# =====================================================================
GOOD_RUN_STATEMENTS = [
    TEMPLATE("1 · 例：Names the real cause, traceable to a record - not a plausible story."),
    TEMPLATE("2 · 例：Gives an outcome consistent with what the records actually say."),
    TEMPLATE("3 · 例：Takes the gated action at most once, and only after the facts are established."),
    TEMPLATE("4 · 例：Says 'I don't know' rather than inventing an answer the records do not support."),
    TEMPLATE("5 · 例：Costs less than a person doing it."),
]

# 每一条对应哪些 case 来验证它。写 case_id 列表，D4 会检查这些 case 存在。
GOOD_RUN_TESTABILITY = {
    1: TEMPLATE("验证第 1 条的 case_id 列表", example=["CLM-8933", "CLM-8894"]),
    2: TEMPLATE("验证第 2 条的 case_id 列表"),
    3: TEMPLATE("验证第 3 条的 case_id 列表"),
    4: TEMPLATE("验证第 4 条的 case_id 列表", example=["CLM-8888", "CLM-8941"]),
    5: TEMPLATE("验证第 5 条的方式（这条通常由 D6 的成本模型回答，不是单个 case）"),
}
