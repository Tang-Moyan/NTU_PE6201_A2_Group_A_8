"""
D5 - USER WORK FILE  ("The model battery")
=====================================================================
两次运行，同一个 harness：

  D5(a)  scripted run —— 确定性、无网络、无 key。
         **BACKEND = "scripted" 必须是提交代码里的默认值。**
         做不到这一点，Technical Execution 直接被封顶。

  D5(b)  live battery —— 至少三个不同的模型，通过 OpenRouter。
         报的不是「哪个模型最好」，而是
         **哪个模型能以什么代价干你们这份活，以及它们在哪里分歧。**
         预期分歧最大的地方是 negative case —— 那就是要找的发现。

预算形状（见 brief 第 7 节）：
  完整评估集 × 1 trial × 3 个模型，外加 negative-only × 3 trials。
  **按人分模型**：一人负责一个模型，用自己的 key 跑。
  6-7 人的话还能再加第四个模型。

进度自查：  python A2_main/D5_model_battery/test_D5.py
=====================================================================
"""
from common.template import TEMPLATE

# =====================================================================
# D5(a) - 可复现的 scripted run
# =====================================================================

SCRIPTED_DEFAULT_CONFIRMED = TEMPLATE(
    "确认提交的 config.py 里 BACKEND = 'scripted'？test_D5.py 会实际检查文件。",
    example=True)

FRESH_CLONE_TESTED = TEMPLATE(
    "确认在**全新 clone**、没有 key 的机器上跑过 `python run_eval.py`？"
    "'works on my laptop' has caught out every cohort so far。"
    "写测试的日期和人。",
    example="2026-09-20, tested by Wei Ling on a clean clone with no "
            "OPENROUTER_API_KEY set")


# =====================================================================
# D5(b) - live battery：至少三个模型
# =====================================================================
# 每个模型一行：
#   slug        OpenRouter 的模型标识，例如 "openai/gpt-4o-mini"
#   owner       哪位组员负责跑（用自己的 key）
#   price_in    每百万 input token 的美元价
#   price_out   每百万 output token 的美元价
#   tier        "cheap" | "mid" | "frontier" —— D6 的盈亏平衡点要用
#
# **价格必须自己去 vendor 页面核对。** scaffold 里的价格标注是
# 2026-08-28 核对的，会过期。引用一个没核实过的价格正是 D6 扣分的地方。
MODELS = [
    # 一人一个模型、一把自己的 key。brief 的两条硬约束：
    #   (1) 至少跨两个价格档，且没有两人使用同一个 family
    #   (2) 评估集与 v2 prompt 每人完全一致，只有 MODEL 这一个字符串不同
    # 价格 2026-09-15 核实于 openrouter.ai/api/v1/models（US$ / 百万 token）。
    # frontier 档（claude-fable-5.1 / gpt-6-astra，10/50）全集约 US$11.70，
    # 超 brief 的每人 US$3 上限，故未排入。
    # qwen/qwen3.8-flash 更便宜但不支持 tool calling，agent 无法使用。
    {"slug": "google/gemini-3.8-flash",      "owner": "Jojo",
     "price_in": 0.75,  "price_out": 3.75,  "tier": "mid"},
    {"slug": "deepseek/deepseek-v4.1-flash", "owner": "Moyan",
     "price_in": 0.15,  "price_out": 0.60,  "tier": "cheap"},
    {"slug": "~openai/gpt-luna-latest",      "owner": "Ziyu",
     "price_in": 0.20,  "price_out": 1.20,  "tier": "cheap"},
    {"slug": "x-ai/grok-4.6",                "owner": "Xianer",
     "price_in": 2.00,  "price_out": 6.00,  "tier": "mid"},
    {"slug": "z-ai/glm-5.3",                 "owner": "Lufei",
     "price_in": 1.40,  "price_out": 4.40,  "tier": "mid"},
    # Keerthi 跑 D2(b) 的 v1 pass，跑在 google/gemini-3.8-flash 上，不占一行模型。
]

PRICES_VERIFIED_ON = TEMPLATE(
    "你们是哪一天、在哪个页面核对的价格？",
    example="2026-09-18, openrouter.ai/models")

BATTERY_SHAPE = TEMPLATE(
    "battery 怎么跑的？brief 期望：full set × 1 trial × 3 models，"
    "外加 negatives-only × 3 trials。",
    example="Full 40-case set, 1 trial, on each of 3 models (120 runs), plus "
            "the 9 negative cases at 3 trials on each model (81 runs).")


# =====================================================================
# 结果与解读 —— 数字由 battery.py 测，你们写解读
# =====================================================================

DIVERGENCE_FINDING = TEMPLATE(
    "三个模型在哪里分歧？**预期就在 negative case 上分歧，这才是要找的发现。**"
    "要具体到 case_id 和 family。",
    example="All three agree on the 31 ordinary cases. They diverge on "
            "prompt injection: the cheap model followed CLM-8952's imitated "
            "tool output on 2 of 3 trials, while the other two escalated "
            "every time. Overall pass rate hides this - the negative-only "
            "pass rate does not.")

WHICH_MODEL_WE_SHIP = TEMPLATE(
    "你们会上哪个模型，为什么？这个结论必须和 D6 的盈亏平衡点一致 —— "
    "test_D5.py 不检查这个，但评分人会读出矛盾。",
    example="The mid-tier model. Our break-even analysis in D6 says the "
            "cheap model must reach 91.2% to be worth its saving, and it "
            "measured 84%.")

VENDOR_NEUTRALITY_NOTE = TEMPLATE(
    "确认代码是 vendor-neutral 的：一个 BACKEND/MODEL/BASE_URL 块，"
    "**且只有一个函数知道有 vendor 存在**。切换模型 = 改一个字符串。"
    "写出那个函数在哪。",
    example="D4_eval_set/scripts.py :: _live_call() is the only function "
            "that knows a vendor exists. config.py holds the three strings.")

# 如果用了 reasoning model（**不推荐**）：thinking token 按 output 计费，
# 而 output 在便宜档是 input 的 4 倍、frontier 档 5 倍。
# 一个悄悄吐 900 个 thinking token 的模型不是「贵一点」，是把账单的形状改了。
REASONING_MODEL_NOTE = TEMPLATE(
    "用了 reasoning model 吗？没有就填 None（推荐）。"
    "用了就必须：说明 cap 到多少、并且**两种方式都报成本**。"
    "OpenRouter 的 reasoning 对象：effort 大致 minimal 10% / low 20% / "
    "medium 50% / high 80%；Anthropic 的 max_tokens 下限是 1024。",
    example=None)

CACHING_NOTE = TEMPLATE(
    "用了 prompt caching 吗？没有就填 None。"
    "**不要建模，要实测**：同一个评估集开和关各跑一次，"
    "token 数从 API 响应里取而不是从价目表推。"
    "注意 cache 只在 prefix 完全不变时命中 —— 在 system prompt 顶上放个"
    "时间戳，就等于悄悄关掉了 caching。",
    example=None)
