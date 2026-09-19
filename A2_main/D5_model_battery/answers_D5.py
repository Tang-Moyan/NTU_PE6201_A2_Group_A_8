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

SCRIPTED_DEFAULT_CONFIRMED = True

FRESH_CLONE_TESTED = TEMPLATE(
    "确认在**全新 clone**、没有 key 的机器上跑过 `python run_eval.py`？"
    "写测试的日期和人。",
    example="2026-09-20, tested by <name> on a clean clone with no "
            "OPENROUTER_API_KEY set")


# =====================================================================
# D5(b) - live battery：至少三个模型
# =====================================================================
MODELS = [
    {"slug": "google/gemini-3.8-flash",      "owner": "Jojo",
     "price_in": 0.75,  "price_out": 3.75,  "tier": "mid"},
    {"slug": "minimax/minimax-m2.7",           "owner": "Moyan",
     "price_in": 0.30,  "price_out": 1.20,  "tier": "cheap"},
    {"slug": "~openai/gpt-luna-latest",      "owner": "Ziyu",
     "price_in": 0.20,  "price_out": 1.20,  "tier": "cheap"},
    {"slug": "x-ai/grok-4.6",                "owner": "Xianer",
     "price_in": 2.00,  "price_out": 6.00,  "tier": "mid"},
    {"slug": "z-ai/glm-5.3",                 "owner": "Lufei",
     "price_in": 1.40,  "price_out": 4.40,  "tier": "mid"},
]

PRICES_VERIFIED_ON = (
    "2026-09-19, openrouter.ai model pages/API; baseline uses undiscounted "
    "list prices (same procurement source as answers_D6)"
)

BATTERY_SHAPE = (
    "Planned: full 45-case set x 1 trial x each declared model, plus "
    "negative-only cases x 3 trials per model. Live results not yet "
    "written back into answers_D5 — see items still needing team input."
)

DIVERGENCE_FINDING = TEMPLATE(
    "三个模型在哪里分歧？**预期就在 negative case 上分歧。**"
    "要具体到 case_id 和 family。需要 D5 live battery 结果。")

WHICH_MODEL_WE_SHIP = TEMPLATE(
    "你们会上哪个模型，为什么？必须和 D6 盈亏平衡点一致。"
    "需要 CHEAP/EXPENSIVE_MEASURED_SUCCESS_RATE。")

VENDOR_NEUTRALITY_NOTE = (
    "D5_model_battery/backends.py :: _live_call() is the only function "
    "that knows a vendor exists. config.py holds BACKEND / MODEL / BASE_URL."
)

REASONING_MODEL_NOTE = None

CACHING_NOTE = None
