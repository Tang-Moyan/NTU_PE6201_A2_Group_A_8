# 报告 —— 工作内容

> 最多 **2000 词**，六节，顺序固定。
> **表格和图不计入，只有正文计。**
> *"Argument, not data."* 数字住在仓库里，报告里放论证。

---

## 这个文件夹里有什么

| 文件 | 是什么 |
|---|---|
| `answers_report.py` | **用户工作文件**：第 6 节 + 六节定稿正文 + 交付物自查 |
| `assemble.py` | 收集各节素材、统计字数、检查预算 |

```bash
python A2_main/report/assemble.py            # 素材 + 字数
python A2_main/report/assemble.py --prose    # 只看定稿正文
```

**工作方式**：先跑 `assemble.py` 看它给出的**素材**（各 D 的答案 + 实测数字），
根据素材写正文，填进 `SECTION_N_PROSE`，再跑一次看字数。

---

## 六节与预算

| # | 章节 | 词数 | 来自 |
|---|---|---|---|
| 1 | Why an agent | 400 | D0 |
| 2 | The tool layer | **450** | D2 |
| 3 | What the evidence showed | 350 | D4 + D5 |
| 4 | What it costs | 400 | D6 |
| 5 | The two failures | 250 | D7 |
| 6 | What we would not deploy | 150 | 局限 + D1 的替代架构 |

### 为什么预算是这个形状

**第 1、2 节合起来 850 词，接近一半**，因为
Conceptual Understanding（25%）和 Reasoning & Justification（25%）合占 rubric 的一半，
而这一半几乎全部落在**「为什么是这一级」**和**「为什么是这套工具」**上。

**第 4 节变大了**，因为成本模型现在有**四个实测杠杆**和**一个要辩护的区间**，
不是一个数字要陈述。

**第 5 节故意短**：两个失败写得紧凑，比两个铺开叙述更有说服力。

### 第 1 节被读得最早也最狠

> *"A report that opens with what the team built, rather than why an agent was
> the right instrument, has skipped the question the whole of Class 4 was
> arranged around."*

不要用「我们构建了一个……」开头。用「这个问题落在第 7 级，因为……」开头。

---

## 每节的具体结构建议

在各个 D 的 `WORKPLAN.md` 末尾，都有一张「报告第 N 节结构建议」的分段表。
去那里看，这里不重复。

---

## 表格全部放仓库

不计入字数，所以**尽量多放**。现成可直接用的（都由脚本打印）：

| 表 | 出处 |
|---|---|
| Class 4 梯子 + 四问 workflow 表 | `D0/framework.py` |
| ground truth 三行表 | `D0/framework.py` |
| turn 敏感度表（同 s、不同 T） | `D0/framework.py` |
| 工具三问评分表 | `D2/tool_audit.py` |
| 工具块 token 表 | `D2/tool_audit.py` |
| v1 vs v2 对比表 | `D2/descriptor_ab.py` |
| **串行 vs 并行表** | `D2/parallel_ab.py` |
| 10 条护栏用例结果表 | `D3/checklist.py` |
| negative family 分布表 | `D4/eval_runner.py` |
| 三个模型对比表 | `D5/battery.py` |
| 三层成本表 + 敏感度表 + 四杠杆账本 | `D6/levers.py` |
| turn 分布直方图 + 前后对比表 | `D7/failure_runs.py` |

正文只写**结论**，表放旁边。

---

## 四个交付物，一个都不能少

归档命名：**`PE6201_A2_[TeamID].zip`**，例如 `PE6201_A2_A-8.zip`。外加视频链接。

| # | 交付物 | 要点 |
|---|---|---|
| 1 | 代码仓库，**两个地方** | (a) 公开仓库（展示 history 和 contribution）+ (b) NTULearn 提交夹里的同样代码副本。**两个都要**——仓库证明过程，副本保证评分不依赖链接还活着 |
| 2 | 报告 | ≤2000 词，六节 |
| 3 | 5 分钟演示 | 系统在跑、**现场展示一个 negative case**、那些数字。**每个成员都要说话**。超时在 Communication 项扣分 |
| 4 | 团队自评表 | **一队一份，不是一人一份**。对照 Rubric 1 打分 + 一段取舍反思。**不计分但必答——缺了就是提交不完整** |

另外：

- **`CONTRIBUTIONS.md`** 必须在仓库里，写明谁做了什么，**且 commit history 能佐证**。第 8 节靠这个
- **README** 要能让一个陌生人从 clone 走到复现 scripted run
- **`results.json` 要提交**，报告里的数字要来自它

> ⚠️ **一个已知的坑**：`A2_main/.gitignore` 里有一行 `results.json`，
> 默认会忽略它，但 scaffold 的 README 又要求提交它。
> 要么删掉那一行，要么 `git add -f A2_scaffold/results.json`。
> `assemble.py` 的自查项里有这一条。

---

## 提交前的检查清单

```bash
# 1 · 全新 clone、没有 key 的机器上
git clone <你们的仓库> /tmp/fresh && cd /tmp/fresh/A2_scaffold
python run_eval.py                      # 必须出数字

# 2 · 数据自洽
python A2_main/data/check_my_data.py

# 3 · 八个交付物无 FAIL
python A2_main/test_all.py

# 4 · 字数没超
python A2_main/report/assemble.py
```

- `BACKEND = "scripted"` 是提交的默认值
- 扩展后的 `expected_outcomes_A.json` 已提交 —— **一个没有配套 key 的 pass rate 不是测量**
- 报告里**每一个 pass rate 都带着它的 trial count**
