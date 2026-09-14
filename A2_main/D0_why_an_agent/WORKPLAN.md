# D0 · 为什么是 agent —— 工作内容

> **这一节是评分人读的第一段，也是报告的第一节。**
> 跳过 D0 直接写代码的团队，已经在两个评分维度上失分了：
> Conceptual Understanding (25%) 和 Reasoning & Justification (25%) 合起来占一半，
> 而这一半几乎全部落在「为什么是这一级」和「为什么是这套工具」上。

---

## 这个文件夹里有什么

| 文件 | 是什么 | 你要动吗 |
|---|---|---|
| `answers_D0.py` | **用户工作文件。D0 唯一需要填的地方** | **要，全部** |
| `reliability.py` | `s = P^(1/T)` 的数学，可直接用的纯函数 | 不用 |
| `framework.py` | 把答案和实测数字拼成报告第 1 节 | 不用 |
| `test_D0.py` | 进度自查 + 数学单元测试 + 论点与实测的一致性检查 | 不用 |

```bash
python A2_main/D0_why_an_agent/test_D0.py       # 还差什么
python A2_main/D0_why_an_agent/framework.py     # 报告第 1 节预览
```

---

## 顺序很重要：D0(c) 必须先提交

`GOOD_RUN_STATEMENTS` 这五条要在**第一个 agent commit 之前**单独 commit 一次。
评分人会看 commit history。建议今天就做这一件事：

```bash
# 只填 answers_D0.py 里的 GOOD_RUN_STATEMENTS，别的先不管
git add A2_main/D0_why_an_agent/answers_D0.py
git commit -m "D0(c): what a good run looks like, before any agent code"
```

五条里**第 4 条最常被漏掉**——「宁可说不知道，也不编造记录不支持的答案」。
它是 D4 negative case 存在的理由。写完自查一遍：这五条里有没有哪一条是不可测的？
不可测就重写，因为 D4 的评估集是这份清单的下游。

---

## D0(a) 要写什么

### 1. 定级并辩护 (`RUNG`, `RUNG_DEFENCE`)

答案几乎肯定是 **rung 7**，但你必须用**本问题的具体机制**论证，不能说「因为它很复杂」。
现成的论据在数据里：

- 一个 claim 带 `lines[]`，**line 数量事先不知道**（shipped 数据里 9 个单 line，6 个 2-4 line）
- `procedures.requires_preauth` 决定**要不要**再打一次 `get_preauthorisation`
- 这个分支是**记录**决定的，不是你们写的

### 2. rung 1-6 的反事实 (`RUNG_COUNTERFACTUAL`)

报告明确要求「rungs 1 to 6 would and would not have delivered」。
每一级一句话，说清它在这个问题上**在哪里失效**。
**第 5 级要认真答**——orchestrator-workers 是最接近的一级，敷衍会被看出来。

### 3. 四个 workflow 问题 (`WORKFLOW_TEST`)

第二行是决定性的：**步骤数是否随输入变化**。填 `no` 就等于承认你该做 workflow。

`STEP_VARIATION_EVIDENCE` 必须用**你们自己评估集里的 case_id**，不能空谈。
shipped 数据里现成的三个对比：

| case | 形态 | 为什么 turn 数不同 |
|---|---|---|
| `CLM-8850` | 单 line，无 preauth | 最短的合法运行 |
| `CLM-8960` | 四 line，无 preauth | 四次 coverage 检查折进一轮 |
| `CLM-8925` | 超年度额度 | 两轮早退——**早退是正确行为，不是被截断的运行** |

`test_D0.py` 会去 `output/D4_eval.json` 读实测 turn 分布来核对你的说法。
如果所有 case 的 turn 数都一样，它会直接告诉你：按这个证据你做的是 workflow。

### 4. 治理悬崖 (`FIRST_IRREVERSIBLE_ACTION`)

悬崖**不在** retrieval → agentic retrieval，而在 agentic retrieval → agent，
也就是**第一次写**的那一刻。我们七个工具里六个只读，`issue_decision_letter` 是唯一的写。
点名它，说清为什么收不回来。

---

## D0(b) 要写什么

### Test 1 · Ground truth 测试

`GROUND_TRUTH_SOURCES` 至少三行，每行三个字段：哪张表、多快回答、是否客观。
候选（都在 `data_A/` 里）：

- `policies.json` 的 `status` 和 `start_date`/`end_date` —— 毫秒级，纯客观
- `preauthorisations.json` 的有效期窗口 —— 毫秒级，纯客观
- `decided_claims.json` 的四要素比对 —— 毫秒级，纯客观
- **member narrative 是否含有指令** —— 既不快也不客观

**最后那一条是诚实分。** 正因为它主观，我们才把 gate 放在发信之前而不是让 loop 自由跑。
`GROUND_TRUTH_VERDICT` 里要把这个对比写出来。

### Test 2 · 那个算术

**这部分的数字不用你算。** 框架会自动读：

- `P` ← `output/D4_eval.json`（D4 的实测 pass rate）
- `T` ← `output/D7_turns.json`（D7 的实测 median turns）
- 然后算 `s = P^(1/T)`，并给出「同样的 s、不同的 T」的敏感度表

你要填三段判断：

| 槽位 | 要回答什么 |
|---|---|
| `ARITHMETIC_READING` | 你们的问题是 step **quality** 还是 step **count**？二选一，决定下一步做 D2(b) 还是 D2(c) |
| `WEAK_STEP_READING` | 框架按「失败前最后一个工具调用」给出候选弱步骤，你判断是哪个，以及选 (a) 修它 还是 (b) 去掉它 |
| `ARITHMETIC_LIMITS` | 说明局限：步骤不独立，各步失败率不同，所以 `s` 是诊断而非常数 |

**报告里值得写的一句话**：弱步骤通常两头都吃亏。返回得差，agent 就会重读、重试、游走——
`s` 降低的同时 `T` 升高。所以一个修复能同时动两项，
这也是 D7 的 loop failure 和这个算术是同一个调查的两端。

---

## 报告第 1 节结构建议（400 词）

D0 对应报告第 1 节，预算 400 词，是六节里第二大的。建议这样切：

| 段 | 内容 | 词数 |
|---|---|---|
| 1 | 定级 + 一句话辩护，落到 `lines[]` 和 `requires_preauth` 上 | 70 |
| 2 | rung 5/6 为什么不选（只展开这两级，1-4 一句话带过） | 90 |
| 3 | 四个 workflow 问题，重点写第二行，带两个 case_id 的实测 turn 数 | 90 |
| 4 | 治理悬崖 + 第一个不可逆动作 | 50 |
| 5 | Test 1：三行 ground truth，一句 verdict（点出 narrative 那条不客观） | 50 |
| 6 | Test 2：`P`、`T`、`s` 三个实测数字 + 「quality 还是 count」的结论一句 | 50 |

**表格和图不计入 2000 词上限，只有正文计。** 所以 ladder 表、workflow 四问表、
ground truth 表、turn 敏感度表都放报告里当图表，正文只写结论。
`framework.py` 打出来的表可以直接截图或转成表格。

D0(c) 的五条不必全文进报告——正文一句话说明它们存在、在哪个 commit、
以及 D4 如何验证即可，五条本身放 repo。
