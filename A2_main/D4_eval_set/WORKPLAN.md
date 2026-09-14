# D4 · 评估集 —— 工作内容

> **这是全组工作量最大、也最需要分工的一项。**
> 30–50 个 case，shipped 给了 15，所以你们要写约 25 个。6–7 人的话每人 5–8 个。
>
> 为什么是 30–50 而不是 10：**一个 10-case 的集合分不出两套策略的好坏。**
> Class 4 的演示集能把「谨慎的 agent」和「看起来像那么回事的 agent」分开，
> 只是因为里面有 negative case——而且 8 个里只有 6 个是普通的。
> **规模是让那个数字有意义的东西。**

---

## 这个文件夹里有什么

| 文件 | 是什么 | 你要动吗 |
|---|---|---|
| `answers_D4.py` | **用户工作文件**：新 fixture 行 + 新标签 + 评估策略 | **要，量最大** |
| `scripts.py` | **★ 逐案例的脚本动作。还差 39 个** | **要，量也大** |
| `harness.py` | ★ 评分器 + 判断队列 | 有 1 个 TODO |
| `sync_fixtures.py` | 把 `answers_D4.py` 同步进 `make_fixtures_A.py` 和答案键 | 不用 |
| `eval_runner.py` | 跑评估集，写 `output/D4_eval.json` | 不用 |
| `test_D4.py` | 先查「集合形状」，再查 agent | 不用 |

数据在 `A2_main/data/`：`data_A/`、`expected_outcomes_A.json`、
`make_fixtures_A.py`、`check_my_data.py`。

```bash
python A2_main/code_todo.py D4
```

---

## 工作循环（每改一次都跑一遍，别攒到最后）

```bash
# 1 · 在 answers_D4.py 里加 EXTRA_CLAIMS 和 EXTRA_LABELS
python A2_main/D4_eval_set/sync_fixtures.py           # 2 · 预览，不写
python A2_main/D4_eval_set/sync_fixtures.py --write   # 3 · 写入
python A2_main/data/make_fixtures_A.py           # 4 · 重新生成 data_A/
python A2_main/data/check_my_data.py             # 5 · 查数据是否自洽
python A2_main/D4_eval_set/eval_runner.py             # 6 · 测量
```

第 2–5 步只要几秒。**每次改动之后都跑**，不要攒到最后。

`check_my_data.py` 抓的四件事全都是**静默失败**：

1. **一个解析不到东西的 id** —— claim 的 `member_id` 谁也匹配不上。工具返回空，agent 对着空推理，**运行看起来完全正常**
2. **shipped 行被改了** —— 它存了每一行的指纹，会点名是哪一行动了
3. **重复 id** —— 两个 `CLM-9001`，其中一个永远找不到
4. **有 case 没标签，或有标签没 case**

---

## 铁律一：只加新 id，绝不改 shipped 行

shipped 的记录是评分人重跑你们 harness 时用的基准，答案键是照着它们写的。
`sync_fixtures.py` 会拒绝写入撞号的行。

id 号段用明显是你们的：

| 表 | 起始号 |
|---|---|
| claims | `CLM-9001` |
| members | `M-7001` |
| policies | `POL-8001` |
| preauthorisations | `PA-9001` |

---

## 铁律二：标签在跑 agent **之前**写

> *"Write the label from the routing table in Appendix A, BEFORE you run the agent.
> A key written from your agent's output measures nothing — it agrees with itself
> by construction."*

当 agent 后来和你们的 key 不一致时，**那才是发现**：要么是真 bug，要么是你们标错了、
应该改掉并说明。两种都值得写进报告。

**没有任何脚本能生成标签。** 一个能算出正确答案的脚本，就是这份作业要你们建的那个 agent。
`check_my_data.py` 只检查标签**存在**，从不检查它**对不对**。

---

## 标签的字段要求

| 字段 | 什么时候必填 | 要求 |
|---|---|---|
| `case_id` | 总是 | 对应 `claim_id` |
| `expected_decision` | 总是 | `approve_in_principle` / `request_document` / `escalate` |
| `trigger` | **escalate 必填** | **只能有一个**。「用对的 trigger 到达对的结论」才算过 |
| `missing` | **request_document 必填** | 要具体：`"pre-authorisation reference for 62480, valid on 2026-09-02"`。**"more information" 得零分** |
| `family` | 总是 | 这个 case 演练哪一个 negative family |
| `must_record` | 总是 | 满分记录除 decision 外还要带什么 |
| `note` | 建议 | 这个 case 为什么在这里 |

`test_D4.py` 会检查这些，包括拦截 `missing: "more information"`。

---

## 有些 case 造不出来，除非你动支撑表

大部分 case 只要一个新 claim 就够。但**让 case 有意思的那个事实往往住在别的表里**。
shipped 数据里只有**一个** lapsed policy、**一个** exclusion 规则、**一个**真 duplicate，
所以只靠 `EXTRA_CLAIMS` 堆出来的集合会反复测同样三个事实。

| 想要的 case | 要动哪张表 |
|---|---|
| 第二个 duplicate | `EXTRA_DECIDED` + 一个匹配它的 claim |
| 不同的 exclusion 规则 | `EXTRA_POLICIES`（新 policy_id）+ `EXTRA_MEMBERS` |
| 第二个 lapsed policy | `EXTRA_POLICIES` + `EXTRA_MEMBERS` |
| 新的 preauth 场景 | `EXTRA_PREAUTHORISATIONS` |
| 自定义文档规则 | `EXTRA_REQUIRED_DOCS` |
| 自己的 procedure | `EXTRA_PROCEDURES`（`requires_preauth` 由你们定，**这个 flag 驱动整个循环**） |

---

## Negative case：floor 是 2，这个规模应该带 6–10

**negative = 正确结论是「拒绝 / 询问 / 升级」而不是「行动」的 case。**

Problem A 的 family 清单（直接来自 problem statement）：

- policy lapsed 或超出有效期
- 一条 line 被 exclusion 挡住而其他正常（**claim 不是简单地全批或全拒**）
- 某 procedure 需要 preauth 而不存在，或存在但在 date of service 之前就过期了
- 各 line 加起来超过剩余年度额度
- 已经判过的 claim 的重复提交
- **member 的自由文本里带着指令**

### 最值钱的那一条

> *"A negative case that ACTUALLY FIRED during your development,
> and changed something, earns explicit credit."*

`NEGATIVE_CASES_THAT_FIRED` 就是记这个的。三个字段：抓到了什么、改了什么。
一个都没有，通常说明 negative 写得还不够狠。

---

## 评估策略

| 设置 | 值 | 为什么 |
|---|---|---|
| `TRIALS_ORDINARY` | 1 | 普通 case 一次就够 |
| `TRIALS_NEGATIVE` | **3** | negative 是会在多次运行间翻转的那些；**一次 trial 分不出真正的拒绝和运气好的拒绝** |

### 混合评分器

- **自动检查**产出那个数字：`decision` 和 `trigger` 的确定性比对，没有模型、没有人、没有意见
- **判断检查**处理 `must_record`：那些条目是**英文散文**，子串匹配是在演戏不是在检查

`WHY_NOT_SUBSTRING` 要写清为什么。例子：
`"approved_total 2180"` 这个子串，在一份写着相反结论但恰好印了这个数字的记录里也会命中。

**如果你们用模型来做判断检查，必须在报告里说明。**
*A model grading a model is a claim that needs defending.*

### 隔离性

每个 case 从干净状态开始，**任何 case 不得依赖前一个 case 跑过**。
scaffold 的 `run_case()` 每次自建 guardrails / transcript / backend，所以这一条已经成立——
但 `eval_runner.py` 会**实际跑两次同一个 case 来证明**，而不是断言它。

---

## 怎么给一个 case 写 script

`eval_runner.py` 现在只能跑 `CLM-8842`，因为只有它有 script。
其他 14 个 shipped case 加上你们新写的约 25 个，**都需要在 `scripts.py` 里加一段**。

**谁写 case 就谁写它的 script**——这是同一件「理解这个 case」的事，做两遍。

优先写这三个，因为别的交付物在等它们：

| case | 为什么优先 |
|---|---|
| `CLM-8941` | D3 的敌意文本用例（直白型注入）没它跑不了 |
| `CLM-8952` | D3 的第二条（伪装成工具输出），比上一个难 |
| `CLM-8925` | 两轮早退的短运行。D0 的「步骤数随输入变化」需要它才可验证 |

写 script 的方法就是**把一个正确 agent 会做的步骤按顺序写下来**。
**如果你写不下来，说明你还没真正理解这个 case**——现在发现比 13 号凌晨两点发现好。

参考 `CLM-8842` 那段的形状：每一步是 `{"thought": ..., "calls": [(工具名, {参数})]}`，
最后一步是 `{"final": {"decision": ..., "reason": ...}}`。
**同一轮里放多个 calls，就是 D2(c) 的并行。**

---

## 报告第 3 节结构建议（350 词，D4 + D5 合用）

| 段 | 内容 | 词数 |
|---|---|---|
| 1 | 集合规模 + negative 分布 + trial 策略（每个 pass rate 都带 trial count） | 70 |
| 2 | 总 pass rate 和 negative pass rate，两个分开报 | 60 |
| 3 | **negative case 抓到了什么** —— 具体那个改了代码的例子 | 80 |
| 4 | D5：三个模型在哪里分歧（**预期就在 negative 上分歧，这才是要找的发现**） | 90 |
| 5 | 判断检查怎么做的、谁做的 | 50 |

表格放 repo：family 分布表、per-case 结果表、模型对比表。
`eval_runner.py` 打出来的可以直接用。
