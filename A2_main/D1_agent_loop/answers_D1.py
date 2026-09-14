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
from common.template import TEMPLATE

# =====================================================================
# 循环本身 - 说清它在哪、怎么跑
# =====================================================================

LOOP_LOCATION = TEMPLATE(
    "循环实现在哪个文件的哪个函数？如果你们没改 scaffold，就照实写。",
    example="D1_agent_loop/agent.py :: run_case() - a hand-rolled while loop, "
            "about 60 lines, no framework.")

LOOP_DESCRIPTION = TEMPLATE(
    "用两三句话描述一轮的形状：thought -> action(s) -> observation(s) -> "
    "repeat -> final。要提到一轮可以携带多个 tool call。",
    example="Each turn the backend returns one thought and a list of tool "
            "calls. The loop executes every call in that list, appends all "
            "observations to the transcript, and asks again. It stops when "
            "the backend returns a final record instead of calls.")

TURN_DEFINITION = TEMPLATE(
    "你们怎么定义一个 turn？这个定义必须和 D2(c)、D6 的算术一致。"
    "scaffold 的约定：turn = 一次工具调用轮；最后写决策记录的那一步不算 turn；"
    "gated action 是一个正常的 turn。CLM-8842 因此是 8 calls / 4 turns。",
    example="A turn is one tool-calling round. The concluding move that "
            "writes the decision record is bookkeeping, not a turn. The "
            "gated action is a turn like any other. CLM-8842 is 8 calls in "
            "4 turns, matching Appendix A.")


# =====================================================================
# 为什么是单 agent - 报告第 6 节的核心段落
# =====================================================================

WHY_SINGLE_AGENT = TEMPLATE(
    "为什么不做 multi-agent？注意：这不是「因为作业禁止」——那是 scope "
    "规则。要给工程理由。可引用 Pre-read 5：Cognition 以 multi-agent 卖点"
    "发布 Devin，之后自己发文更正（Don't Build Multi-Agents, 2025-06；"
    "Multi-Agents: What's Actually Working, 2026-04，其中 review agent 是"
    "multi-agent 但写操作保持单线程）。",
    example="Our writes are single-threaded by design: one decision, one "
            "gate, one record. Cognition's own correction is that review can "
            "fan out but writes should not, and our only write is the "
            "decision letter.")

# 报告第 6 节明确要求："a paragraph on an architecture you did not build -
# what it would have caught, what it would have cost, why you stayed
# single-agent." 三个都要答，缺一个就少分。
ALTERNATIVE_ARCHITECTURE = {
    "what_we_did_not_build": TEMPLATE(
        "你考虑过但没建的架构是什么？要具体。",
        example="A second agent reviewing the decision record before the "
                "gate - an evaluator pass over our own output."),
    "what_it_would_have_caught": TEMPLATE(
        "它能抓到你们哪一个真实失败？必须指名 D7 或 D4 里的具体 case，"
        "不能泛泛说'提高质量'。",
        example="Failure 2 in D7: the run that cited an expired "
                "pre-authorisation as if it were valid. A reviewer reading "
                "the record against preauthorisations.json would have "
                "caught it."),
    "what_it_would_have_cost": TEMPLATE(
        "代价是多少？给数字：多一次完整 prompt 的 input token，乘以运行次数。"
        "用 D6 的价格算。",
        example="One extra full-context call per run - roughly +40% input "
                "tokens on our median run, and a second failure surface we "
                "would have to test."),
    "why_we_stayed": TEMPLATE(
        "为什么最终没做？",
        example="The same failure was cheaper to fix at the tool interface, "
                "which is where D7 put it."),
}


# =====================================================================
# Scope boundary - 确认你们没有跑偏
#   下面每一条都不得分，而且每一条都是耗光两周的方式。
#   填 True 表示"我们确认没做这个"。test_D1.py 会检查。
# =====================================================================

SCOPE_CONFIRMATIONS = {
    "no_letter_or_document_generator": TEMPLATE(
        "确认 issue_decision_letter 只写一条 log record，不生成任何信件"
        "文本？填 True/False", example=True),
    "no_user_interface": TEMPLATE("确认没有任何 UI / 网页 / 移动端？", example=True),
    "no_real_irreversible_action": TEMPLATE(
        "确认没有真实发信 / 真实付款 / 写入任何线上系统？这是硬规则。",
        example=True),
    "fixture_data_only": TEMPLATE(
        "确认工具只读本机 fixture 数据，没有碰任何真人记录？", example=True),
    "no_network_needed_for_scripted_run": TEMPLATE(
        "确认 scripted run 不需要网络和 key？D5(a) 全靠这条。", example=True),
}

# 如果你们确实加了一个联网工具（可选，且不推荐），必须说明 record-and-replay
# 怎么做的。没加就填 None。
NETWORK_TOOL_NOTE = TEMPLATE(
    "加了联网工具吗？没有就填 None。加了就说明：调用一次、把响应作为 "
    "fixture 提交、scripted backend 回放。",
    example=None)
