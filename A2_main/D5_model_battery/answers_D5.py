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

# =====================================================================
# D5(a) - 可复现的 scripted run
# =====================================================================

SCRIPTED_DEFAULT_CONFIRMED = True

FRESH_CLONE_TESTED = (
    "2026-09-20, tested by Tang Moyan on a clean working tree with "
    "BACKEND=scripted and no OPENROUTER_API_KEY in the environment; "
    "python A2_main/run_eval.py and D5 scripted battery both completed."
)


# =====================================================================
# D5(b) - live battery：至少三个模型
# =====================================================================
MODELS = [
    {"slug": "google/gemini-3.8-flash",      "owner": "Jojo",
     "price_in": 0.75,  "price_out": 3.75,  "tier": "mid"},
    {"slug": "openai/gpt-4o-mini",            "owner": "Moyan",
     "price_in": 0.15,  "price_out": 0.60,  "tier": "cheap"},
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
    "Delivered: full 45-case set x 1 ordinary trial + negatives x 3 "
    "(81 trials) per live model. Six shards merged into "
    "output/D5_battery.json: glm-5.3 77.8%, grok-4.6 72.8%, "
    "gemini-3.8-flash 50.6%, gemini v1-descriptor 43.2%, "
    "gpt-luna-latest 42.0%, gpt-4o-mini 33.3%."
)

DIVERGENCE_FINDING = (
    "Models diverge hardest on negative families, not on ordinary "
    "approvals. On preauth_expired, glm-5.3 / grok pass 6/6 while "
    "gpt-4o-mini and gemini-v2 both sit at 0/6 (e.g. CLM-8894): the "
    "cheap and mid models treat expired PAs as hard policy failures or "
    "stop early, instead of request_document. On partly_payable "
    "(CLM-8842 / CLM-9005) glm reaches 3/3 while gpt-4o-mini is 0/3 - "
    "mini escalates after claim+policy with trigger outside_policy_dates "
    "even when DOS is in range. Duplicate_of_decided_claim is another "
    "split: glm/grok/gemini 6/6, gpt-4o-mini 0/6. Shared weakness: "
    "annual_limit_exceeded and all three prompt_injection families stay "
    "near 0% even for glm - so the battery shows both model-tier gaps "
    "and a prompt/grading contract the whole set still fails."
)

WHICH_MODEL_WE_SHIP = (
    "We would ship z-ai/glm-5.3 (Lufei, 77.8% / 66.7% on negatives), not "
    "the cheap arm. D6 break-even against the gemini mid-tier baseline "
    "needs ~50.5% success; gpt-4o-mini measured 33.3% (17 points short), "
    "so its ~9x cheaper tokens are erased by US$7.60 escalations. glm "
    "beats gemini on the same harness without collapsing the cost model: "
    "layer 2 still dominates, and accuracy - not list price - decides."
)

VENDOR_NEUTRALITY_NOTE = (
    "D5_model_battery/backends.py :: _vendor_http() is the only network "
    "call site (chat + generation usage). _live_call builds the request; "
    "config.py holds BACKEND / MODEL / BASE_URL."
)

REASONING_MODEL_NOTE = None

CACHING_NOTE = None
