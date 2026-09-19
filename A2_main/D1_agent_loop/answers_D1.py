"""
D1 - USER WORK FILE  ("The agent, and the architecture")
=====================================================================
D1 的代码大部分已经在 D1_agent_loop/agent.py 里跑通了。这里要填的是
**架构论证**——评分人读的是「你为什么这样搭」，不是「你搭了什么」。

其中 ALTERNATIVE_ARCHITECTURE 直接进报告第 6 节，是明确的加分项：
ILO 3 考的就是评估设计替代方案。

进度自查：  python A2_main/D1_agent_loop/test_D1.py
=====================================================================
"""

# =====================================================================
# 循环本身 - 说清它在哪、怎么跑
# =====================================================================

LOOP_LOCATION = (
    "D1_agent_loop/agent.py :: run_case() - a hand-rolled while loop, "
    "about 60 lines, no agent framework."
)

LOOP_DESCRIPTION = (
    "Each turn the backend returns one thought and a list of tool calls. "
    "The loop executes every call in that list, appends all observations "
    "to the transcript, and asks again. It stops when the backend returns "
    "a final record instead of calls."
)

TURN_DEFINITION = (
    "A turn is one tool-calling round. The concluding move that writes the "
    "decision record is bookkeeping, not a turn. The gated action is a turn "
    "like any other. CLM-8842 is 7 calls in 4 turns after cutting "
    "lookup_hospital (previously 8/4), matching Appendix A's convention."
)


# =====================================================================
# 为什么是单 agent - 报告第 6 节的核心段落
# =====================================================================

WHY_SINGLE_AGENT = (
    "Our writes are single-threaded by design: one decision, one gate, one "
    "record. Cognition's own correction is that review can fan out but "
    "writes should not, and our only write is the decision letter."
)

ALTERNATIVE_ARCHITECTURE = {
    "what_we_did_not_build": (
        "A second agent reviewing the decision record before the gate - an "
        "evaluator pass over our own output."
    ),
    "what_it_would_have_caught": (
        "D7 Failure 2 (fat_observation on CLM-8842): a reviewer reading the "
        "record against the projected check_coverage return would have "
        "noticed the agent was reasoning over hundreds of unused table "
        "rows. The same shape of review would also catch an expired "
        "pre-authorisation treated as valid."
    ),
    "what_it_would_have_cost": (
        "One extra full-context call per run - roughly +40% input tokens on "
        "our median 3-turn run (the whole transcript re-sent), and a second "
        "failure surface we would have to test across the 45-case set."
    ),
    "why_we_stayed": (
        "The same failure was cheaper to fix at the tool interface "
        "(filtered returns), which is where D7 put Failure 2. A second "
        "agent would pay forever for a constraint we can enforce once."
    ),
}


# =====================================================================
# Scope boundary
# =====================================================================

SCOPE_CONFIRMATIONS = {
    "no_letter_or_document_generator": True,
    "no_user_interface": True,
    "no_real_irreversible_action": True,
    "fixture_data_only": True,
    "no_network_needed_for_scripted_run": True,
}

NETWORK_TOOL_NOTE = None
