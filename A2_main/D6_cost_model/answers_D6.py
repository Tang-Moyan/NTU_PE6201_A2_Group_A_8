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
PRICE_IN_PER_M = TEMPLATE(
    "主力模型每百万 input token 的美元价", example=0.10)
PRICE_OUT_PER_M = TEMPLATE(
    "主力模型每百万 output token 的美元价。注意 output 通常是 input 的 "
    "4-5 倍，这在有 reasoning token 时会改变账单的形状。", example=0.40)
PRICES_CHECKED_ON = TEMPLATE(
    "哪一天、在哪核对的？", example="2026-09-18, openrouter.ai/models")


# =====================================================================
# Layer 2 的输入：一次失败值多少钱
# =====================================================================
# failure_cost = hourly rate × minutes per escalation ÷ 60
# **不要猜，用人工成本算。**
# Appendix A 给了每个问题一个默认角色和处理时长；用它，或者换成你们自己的
# 并说明为什么。Problem A 的 worked example 用的是 US$7.60 一次。
ESCALATION_ROLE = TEMPLATE(
    "谁来处理一次升级？", example="a claims assessor")
HOURLY_RATE_USD = TEMPLATE(
    "该角色的时薪（美元）", example=38.0)
MINUTES_PER_ESCALATION = TEMPLATE(
    "处理一次升级要多少分钟？", example=12)
FAILURE_COST_SOURCE = TEMPLATE(
    "这两个数从哪来？Appendix A 还是你们自己的假设？自己的要说明理由。",
    example="Appendix A's default for Problem A: a claims assessor at "
            "US$38/hour, 12 minutes per escalation, giving US$7.60.")


# =====================================================================
# Layer 3：固定月度成本
# =====================================================================
# 随规模摊薄的那一层。写 {项目: 每月美元}。
FIXED_MONTHLY = TEMPLATE(
    "固定月度成本明细。要包含**你们自己的 eval 运行**——那也是钱。",
    example={"storage_and_infra": 15.0,
             "evaluation_runs": 8.0,
             "monitoring": 10.0,
             "maintenance_amortised": 40.0})

TASKS_PER_MONTH = TEMPLATE(
    "你们这个问题每月处理多少个 task？报告第 4 节要求给出"
    "「at your problem's volume」的月度数字。"
    "Problem A 的情境说 volume has doubled，给一个有依据的数并说明依据。",
    example=4000)


# =====================================================================
# 三个 cap —— 报告要求和成本模型一起陈述
# =====================================================================
CAPS = {
    "step_cap": TEMPLATE("每次运行的轮数上限。和 D3 的 LIMITS 保持一致。",
                         example=8),
    "budget_ceiling": TEMPLATE("每次运行的 token 上限。和 D3 一致。",
                               example=60000),
    "monthly_limit_per_user": TEMPLATE(
        "每个用户每月的上限。我们选择：写成政策承诺，不在 Guardrails 里 "
        "enforce（单次运行的对象看不到跨 run 的月度用量）。陈述数值 + "
        "单位 + 明确说它不是代码控制。",
        example="200 claims per assessor account per month (policy "
                "commitment, not a code control). Enforced at account "
                "provisioning / ops quota, not inside the per-run "
                "Guardrails instance."),
}


# =====================================================================
# 盈亏平衡点：便宜模型要多准才值得选
# =====================================================================
# 三个量，你们在 D5 都已经有了：
#   C  便宜模型跑一次的成本 —— **只算 token**
#   E  贵模型一次**成功** task 的成本 —— 它自己的 layer1 + layer2
#   F  一次失败的成本 —— 上面算出来的 failure_cost
CHEAP_MODEL = TEMPLATE(
    "便宜档模型的 slug。和 answers_D5.MODELS 里的一个对上。",
    example="openai/gpt-4o-mini")
EXPENSIVE_MODEL = TEMPLATE(
    "贵档模型的 slug。", example="anthropic/claude-3-5-sonnet")

# 如果 D5 的 live battery 还没跑，这两个填 None，框架会跳过并提示。
CHEAP_MEASURED_SUCCESS_RATE = TEMPLATE(
    "便宜模型在你们评估集上的实测 pass rate（0-1 的小数）。没跑就填 None。",
    example=0.84)
EXPENSIVE_MEASURED_SUCCESS_RATE = TEMPLATE(
    "贵模型的实测 pass rate。没跑就填 None。", example=0.92)

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
        "before": TEMPLATE("砍工具之前的 tool definition token 数。"
                           "tool_audit.py 会给你现在的数。"),
        "after": TEMPLATE("砍完之后的 token 数"),
        "note": TEMPLATE("砍了什么、为什么")},
    2: {"what": "Turn count (T) - the quadratic term, the biggest lever",
        "built_in": "D2(c)",
        "before": TEMPLATE("串行的总轮数 / input token 数。"
                           "parallel_ab.py 已经测出来了"),
        "after": TEMPLATE("并行的总轮数 / input token 数"),
        "note": TEMPLATE("依赖规则把线画在哪")},
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

DOMINANT_LEVER = TEMPLATE(
    "哪个杠杆主导了你们的账单？**以及你们怎么知道的。**",
    example="Lever 2. Our sequential arm cost 65% more input tokens than the "
            "parallel one on the same work, and it breached the budget "
            "ceiling. Lever 1 is only ~1,500 tokens per turn by comparison.")


# =====================================================================
# 两个不属于 baseline 的调整
# =====================================================================
# 先报 baseline。如果下面哪一条适用，把调整后的数字**并排**报出来并说明改了什么。
CACHING_MEASURED = TEMPLATE(
    "用了 prompt caching 吗？没有填 None。"
    "**不要建模，要实测**：同一个评估集开/关各跑一次，"
    "token 数从 API 响应取，不从价目表推。"
    "机制、折扣和计费方式**因 vendor 和模型而异，而且会变**："
    "有的自动缓存，有的要你标记块，有的先收一笔写入费才开始省，有的几分钟就过期。"
    "还有最小可缓存尺寸，而且 **cache 只在 prefix 完全不变时命中** —— "
    "在 system prompt 顶上放个时间戳，就等于悄悄关掉了 caching。",
    example=None)

REASONING_MODEL_MEASURED = TEMPLATE(
    "用了 reasoning model 吗？没有填 None（**推荐不用**）。"
    "thinking token 按 output 计费，而 output 在便宜档是 input 的 4 倍、"
    "frontier 档 5 倍。一个悄悄吐 900 个 thinking token 的模型不是"
    "「贵一点」，它把账单的**形状**改了。"
    "怎么看出来：读 API 返回的 usage 块，不要读你自己的估计。"
    "用了就必须 cap，说明 cap 到多少，并且两种方式都报成本。",
    example=None)
