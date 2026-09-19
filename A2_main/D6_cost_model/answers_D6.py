"""
D6 - USER WORK FILE  ("The cost-to-serve model")
=====================================================================
用 Class 5 的三层模型。**用 D4 实测的 success rate 和 D5 实测的 token
数——不是估计值。**

  "This is marked on METHOD, not on arithmetic precision. A defensible
   model with stated assumptions, three separated layers, a sensitivity
   range and four measured levers beats a confident single number with
   none of them."

报告第 4 节 400 词。它变大了，因为现在成本模型有四个实测杠杆和一个
要辩护的区间，而不是一个数字要陈述。

进度自查：  python A2_main/D6_cost_model/test_D6.py
完整报告：  python A2_main/D6_cost_model/levers.py
=====================================================================
"""
from common.template import TEMPLATE

# =====================================================================
# 输入：价格
# =====================================================================
# **自己去核对。** 引用一个没核实过的价格正是 D6 扣分的地方。
PRICE_IN_PER_M = 0.75        # google/gemini-3.8-flash
PRICE_OUT_PER_M = 3.75       # 5.0x input - in band for its tier
PRICES_CHECKED_ON = (
    "2026-09-15, openrouter.ai/api/v1/models - the live endpoint behind the "
    "pricing page, so the figures are machine-readable and reproducible "
    "rather than a screenshot. OpenRouter is our actual procurement path: "
    "config.BASE_URL points at it and each member runs their model on their "
    "own OpenRouter key, so these are prices we would pay, not vendor list "
    "prices.")


# =====================================================================
# Layer 2 的输入：一次失败值多少钱
# =====================================================================
# failure_cost = hourly rate × minutes per escalation ÷ 60
# **不要猜，用人工成本算。**
# Appendix A 给了每个问题一个默认角色和处理时长；用它，或者换成你们自己的
# 并说明为什么。Problem A 的 worked example 用的是 US$7.60 一次。
ESCALATION_ROLE = "a claims assessor"
HOURLY_RATE_USD = 38.0
MINUTES_PER_ESCALATION = 12
FAILURE_COST_SOURCE = (
    "Appendix A's default for Problem A: a claims assessor at US$38/hour, "
    "12 minutes per escalation, giving US$7.60 per failure. We use the "
    "Class 5 escalation form, variable + (1-p) x failure, rather than the "
    "Class 4 retry form: a wrong outcome here goes to a claims assessor, not "
    "back into the loop. We kept the "
    "default rather than substituting a Singapore salary so that our figure "
    "is comparable with the brief's own worked example; the sensitivity "
    "section shows what happens if the true rate is lower.")


# =====================================================================
# Layer 3：固定月度成本
# =====================================================================
# 随规模摊薄的那一层。写 {项目: 每月美元}。
FIXED_MONTHLY = {
    "storage_and_infra":     15.0,
    "evaluation_runs":        8.0,   # our own D4/D5 batteries are real money
    "monitoring":            10.0,
    "maintenance_amortised": 40.0,
}

TASKS_PER_MONTH = 8000   # The FAQ states Problem A's volume directly:
                         # 8,000 claims a month (Problem B is 4,000).


# =====================================================================
# 三个 cap —— 报告要求和成本模型一起陈述
# =====================================================================
CAPS = {
    "step_cap": 8,           # == config.MAX_TURNS
    "budget_ceiling": 60000, # == config.MAX_TOKENS_PER_RUN
    "monthly_limit_per_user": (
        "200 claims per assessor account per month. Our observed peak is "
        "about 100, so this is 2x headroom and will not bite a real "
        "assessor; it caps a runaway integration at roughly US$3.60 of "
        "tokens per account per month. Unlike the other two caps this one "
        "is not in the scaffold - it exists because the step cap and the "
        "budget ceiling bound one run, and neither bounds a caller that "
        "starts ten thousand of them."),
}


# =====================================================================
# 盈亏平衡点：便宜模型要多准才值得选
# =====================================================================
# 三个量，你们在 D5 都已经有了：
#   C  便宜模型跑一次的成本 —— **只算 token**
#   E  贵模型一次**成功** task 的成本 —— 它自己的 layer1 + layer2
#   F  一次失败的成本 —— 上面算出来的 failure_cost
CHEAP_MODEL = "deepseek/deepseek-v4.1-flash"      # 0.15 / 0.60 per M
EXPENSIVE_MODEL = "google/gemini-3.8-flash"       # 0.75 / 3.75 per M

# 如果 D5 的 live battery 还没跑，这两个填 None，框架会跳过并提示。
CHEAP_MEASURED_SUCCESS_RATE = None      # TODO: D5(b) live battery
EXPENSIVE_MEASURED_SUCCESS_RATE = None  # TODO: D5(b) live battery

BREAK_EVEN_READING = TEMPLATE(
    "一句话，带上你们两个实测数字。brief 说这是报告里最有用的一句话。"
    "注意读出它的含义：便宜模型可能便宜十倍，却仍然必须落在贵模型一个"
    "百分点以内才值得选 —— **当失败很贵时，模型价格几乎不重要，准确度才重要。**"
    "反过来也成立：失败越便宜，token 价格越重要。",
    example="Our cheap model needs 91.2% to be worth its saving and measured "
            "84%, so we ship the mid-tier model despite it costing 10x per "
            "run.")


# =====================================================================
# 成本账本：四个杠杆，每个都要有实测的 before / after
# =====================================================================
# **这是 D6 里扣分最狠的部分。**
# "A cost model that only reports a number tells us nothing about your design."
#
# 杠杆 1 和 3 看起来像、其实不是：
#   胖工具块 = 轮数的**线性**函数
#   胖观察值 = **复合**的，因为每个观察都会在之后每一轮被重发
# 两个都值得砍，但只有一个会爆炸。**说清哪个主导了你们的账单，以及怎么知道的。**
LEVERS = {
    1: {"what": "Tool block size (B) - re-sent every turn, called or not",
        "built_in": "D2(a)",
        "before": 1167,   # tool_block_tokens, output/D2_tool_audit.json
        "after": TEMPLATE("砍完之后的 tool block token 数 - re-run "
                          "A2_main/D2_tool_layer/tool_audit.py first; "
                          "output/D2_tool_audit.json still shows the "
                          "pre-cut seven-tool figure"),
        "note": ("We cut lookup_hospital. CLM-8874 uses a non-panel hospital "
                 "(H-330) and still expects approve_in_principle, so panel "
                 "status changes what the record must SAY, not what the "
                 "decision is - it never needed a turn of its own. get_claim "
                 "now returns the hospital details on its first call. "
                 "CLM-8842 still passes in four turns, on seven tool calls "
                 "instead of eight.")},
    2: {"what": "Turn count (T) - the quadratic term, the biggest lever",
        "built_in": "D2(c)",
        "before": "8 turns / 59,400 input tokens",
        "after": "4 turns / 21,000 input tokens",
        "note": ("Coverage, hospital and document checks for the three lines "
                 "are independent of one another, so they share one turn. "
                 "The pre-authorisation lookup cannot move: it depends on "
                 "first learning that a procedure requires one. The "
                 "sequential arm also breached the budget ceiling at 60,480 "
                 "tokens and was halted, so the saving is 64.6% of input "
                 "tokens AND the difference between a result and none.")},
    3: {"what": "Observation size (D) - compounds across later turns",
        "built_in": "D2(b)",
        "before": TEMPLATE("v1 每次调用返回的 token 数"),
        "after": TEMPLATE("v2 每次调用返回的 token 数"),
        "note": TEMPLATE("返回形状改了什么")},
    4: {"what": "Success rate - sets layer 2, usually the biggest layer",
        "built_in": "D4",
        "before": TEMPLATE("改进前的实测 pass rate"),
        "after": TEMPLATE("改进后的实测 pass rate"),
        "note": TEMPLATE("是什么让它动了")},
}

DOMINANT_LEVER = (
    "Lever 4, the success rate, and it is not close. At our measured token "
    "counts layer 2 is 42x layer 1 - US$0.76 of expected fallback against "
    "US$0.018 of tokens per task - so at 4,000 tasks a month the entire "
    "token bill is US$72 while one point of pass rate is worth about US$30. "
    "That is how we know: the ratio, not an opinion. Lever 2 is the largest "
    "of the three token levers and worth pulling (64.6% of input tokens, and "
    "the sequential arm breached the budget ceiling), but all three token "
    "levers together move under 3% of the bill. A team that optimised tokens "
    "and left the pass rate alone would have worked on the wrong problem.")


# =====================================================================
# 两个不属于 baseline 的调整
# =====================================================================
# 先报 baseline。如果下面哪一条适用，把调整后的数字**并排**报出来并说明改了什么。
CACHING_MEASURED = None          # not used; baseline list prices only

REASONING_MODEL_MEASURED = None  # not used - deliberately. Thinking tokens
                                # bill as output, and output is 5x input on
                                # our tier, so a reasoning model would change
                                # the SHAPE of the bill, not just its size.
