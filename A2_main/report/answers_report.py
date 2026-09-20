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
from common.template import TEMPLATE

# =====================================================================
# 提交信息
# =====================================================================
TEAM_ID = TEMPLATE("团队编号，例如 'A-8'。归档名要用它：PE6201_A2_[TeamID].zip",
                   example="A-8")
PROBLEM_CHOSEN = "A"          # 这个仓库已经只做 Problem A，不用改

REPO_URL = TEMPLATE(
    "公开仓库地址（GitHub 或同类）。**两个地方都要有**："
    "(a) 公开仓库展示 history 和 contribution，"
    "(b) NTULearn 提交文件夹里放同样的代码副本 —— "
    "这样评分不依赖某个链接还活着。",
    example="https://github.com/.../NTU_PE6201_A2_Group_A_8")

VIDEO_URL = TEMPLATE(
    "5 分钟演示视频链接。要求：系统在跑、**现场展示一个 negative case**、"
    "以及那些数字。**每个成员都要说话。** 超时会在 Communication 项扣分。")


# =====================================================================
# 第 6 节 · What we would not deploy  (150 词)
# =====================================================================
# 两部分，缺一个就少分：
#   (a) 你们发现的局限
#   (b) **一段关于你们没建的架构** —— 它本可以抓到什么、代价多少、
#       为什么最终保持单 agent
# (b) 的素材在 answers_D1.ALTERNATIVE_ARCHITECTURE，这里写成段。

LIMITS_WE_FOUND = TEMPLATE(
    "你们发现的局限。要具体，不要写「还可以进一步优化」。"
    "好的素材：narrative 判断那一步既不快也不客观；"
    "substring 匹配的注入检测很脆；scripted backend 测不了 prompt 的效果。",
    example="Our injection detection is substring matching, which CLM-8952 "
            "already defeats once by imitating a tool result rather than "
            "issuing an instruction. We widened it; we do not believe it "
            "generalises, and we would not deploy it against an adversary "
            "who knows it is there.")

WOULD_NOT_DEPLOY = TEMPLATE(
    "在什么条件下你们**不会**把它上线？一句话，要有实际约束。",
    example="Not at autonomy='act'. Our confirm gate is doing real work: "
            "the narrative check is the one input we cannot verify against "
            "a record, and it is the one an outsider controls.")


# =====================================================================
# 各节定稿正文
# =====================================================================
# 先跑 assemble.py 看素材，再回来写这里。留 None 时 assemble.py 会
# 显示素材而不是正文。
#
# 预算是指导，2000 词是硬上限。
SECTION_1_PROSE = """Rungs 1–6 are insufficient for this health-insurance claims workflow because improving an individual model response does not guarantee a correct, bounded, end-to-end decision. A real claim requires the system to retrieve documents, confirm policy status, apply coverage rules and exclusions, calculate the payable amount, and choose whether to approve, deny, or escalate. Each transition depends on earlier evidence and must remain auditable. A larger model, longer prompt, fixed chain, retrieval, or tool access in isolation does not provide the planning, state tracking, evidence checks, bounded retries, and human gate needed when evidence is missing, contradictory, stale, or hostile. The D2 comparison makes this operational: for case CLM-8842, the serial design took eight turns and 59,400 input tokens and stopped at the 60,480-token budget, whereas parallel calls completed in four turns with 21,000 input tokens. The problem is therefore orchestration and control, not simply model capability.

On the scripted evaluation, the end-to-end pass rate was P = 1.000 across a three-step decision path (T = 3). Under the simplifying assumption that steps are independent and equally reliable, P = s^T, so the implied per-step reliability is s = P^(1/T) = 1.000^(1/3) = 1.000. This is an exact 1.0 on the scripted set, not a production guarantee. All 81 scripted trials passed the code check, but the fixed backend and absence of observed failures do not measure distribution shift, ambiguous evidence, tool outages, or new prompt-injection wording. Reliability also compounds quickly: if each of six steps were 0.98 reliable, end-to-end reliability would be only 0.98^6 = 0.886. An agent is justified only when its autonomy is surrounded by measurable controls.

We therefore define a good run using five observable statements:
(1) It retrieves the correct claim and policy records and relies only on current, authoritative evidence.
(2) It selects the necessary tools, parallelises independent calls, and avoids duplicate or irrelevant work.
(3) It remains within turn, token, and cost limits, stopping with an explicit, auditable reason if a limit or dependency fails.
(4) It treats claimant and provider text as untrusted, resists prompt injection, and never allows external text to alter system rules or trigger an irreversible action.
(5) It produces a consistent approve, deny, or escalate decision with supporting evidence, a checked calculation, recorded uncertainty, and human review before payment or final rejection."""
sSECTION_2_PROSE = TEMPLATE("第 2 节 The tool layer 定稿正文（约 450 词）")
SECTION_3_PROSE = """We evaluated 45 labelled health-insurance claims. Ordinary cases ran once and negative cases ran three times, giving 81 scripted trials. All 81 passed the deterministic decision and trigger checks. GPT-5.6-sol then reviewed the first-trial decision records against Appendix A, the fixture evidence and each must_record requirement. All 45 records passed this semantic review. The live battery produced much lower scores. Grok achieved 72.8%, Gemini achieved 50.6%, Luna achieved 42.0%, and GPT-4o-mini achieved 33.3%. Grok was the strongest model but also the most expensive at US$2.5233. Its negative-case pass rate was 66.7%. Grok failed 22 trials. Ten failures came from invalid JSON structure. Twelve used a correct escalation decision but a non-canonical trigger name. For example, the model returned instruction_in_narrative instead of instruction_in_member_narrative. This exposed a prompt-contract weakness rather than only an insurance-reasoning failure.
The evaluation set deliberately varies the decision routes rather than only collecting ordinary approvals. It includes missing documents, absent or expired pre-authorisation, lapsed and out-of-date policies, annual-limit boundaries, non-panel providers, duplicates, exclusions, and three prompt-injection claims. The guardrail checklist complements this task-level evaluation. All 10 guardrail cases held: the turn cap stopped a four-turn run when the cap was reduced to three; the budget ceiling stopped a 21,600-token run at a 10,800-token ceiling; and duplicate-action detection stopped a repeated tool call. These outcomes show that the controls fail loudly with an auditable reason instead of silently returning an incomplete answer.\n\nThe autonomy tests demonstrate why the gate is located at the irreversible action. Under suggest, the system held the decision letter; under act, the record explicitly showed that the gate was reached and passed. The three hostile-text cases covered a direct instruction to ignore exclusions, fabricated text that imitated a coverage-tool result, and a command to approve while skipping policy checks. Each was escalated with the trigger instruction_in_member_narrative rather than being allowed to steer the decision. Together, the results support a bounded workflow that can gather evidence autonomously, but they also show why human confirmation and adversarial testing remain necessary before any insurer commitment."""
SECTION_4_PROSE = TEMPLATE("第 4 节 What it costs 定稿正文（约 400 词）")
SECTION_5_PROSE = TEMPLATE("第 5 节 The two failures 定稿正文（约 250 词）")
SECTION_6_PROSE = TEMPLATE("第 6 节 What we would not deploy 定稿正文（约 150 词）")


# =====================================================================
# 其余三个交付物的自查
# =====================================================================
CONTRIBUTIONS_MD_WRITTEN = TEMPLATE(
    "仓库里有 CONTRIBUTIONS.md，写明谁做了什么，**且 commit history 能佐证**？"
    "第 8 节靠这个。True/False", example=False)

SELF_APPRAISAL_DONE = TEMPLATE(
    "团队自评表完成了吗？**一队一份，不是一人一份**，对照 Rubric 1 打分"
    "并附一段关于取舍的反思。不计分但**必答** —— 缺了就是提交不完整。",
    example=False)

RESULTS_JSON_COMMITTED = TEMPLATE(
    "A2_main/results.json 提交了吗？报告里的数字要来自它。"
    "（scaffold 原本的 .gitignore 会忽略它，A2_main 的 .gitignore 已经"
    "去掉了那条规则——跑一次 run_eval.py 然后 git add 即可。）",
    example=False)
