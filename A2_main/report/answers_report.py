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
SECTION_1_PROSE = TEMPLATE("第 1 节 Why an agent 定稿正文（约 400 词）")
SECTION_2_PROSE = TEMPLATE("第 2 节 The tool layer 定稿正文（约 450 词）")
SECTION_3_PROSE = TEMPLATE("第 3 节 What the evidence showed 定稿正文（约 350 词）")
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
