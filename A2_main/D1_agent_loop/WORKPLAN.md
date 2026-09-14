# D1 · Agent 与架构 —— 工作内容

> **好消息：D1 的代码已经在这个文件夹里，而且跑通了。**
> `agent.py` 就是那个手写的 ReAct 循环，支持一轮多个工具调用。
> D1 剩下的工作主要是**论证**和**别跑偏**。

---

## 这个文件夹里有什么

| 文件 | 是什么 | 你要动吗 |
|---|---|---|
| `agent.py` | **★ ReAct 循环本体。这是被评分的东西** | 读懂；有 2 个 TODO |
| `answers_D1.py` | **用户工作文件**：架构论证 + scope 确认 | **要** |
| `loop_contract.py` | 八条循环契约的验证代码，跑真实 case | 不用 |
| `test_D1.py` | 跑契约 + 打印 turn 形状 + 进度自查 | 不用 |

```bash
python A2_main/code_todo.py D1     # agent.py 里标了什么
```

**`agent.py` 只有六十来行，读完再改。** 这是 D1 的全部——
一个被库接管的循环，就是一个没有你们东西可评分的循环。

```bash
python A2_main/D1_agent_loop/test_D1.py
A2_CASE=CLM-8960 python A2_main/D1_agent_loop/test_D1.py   # 换个 case 验证
```

**每次改完 `D1_agent_loop/agent.py` 都跑一次这个脚本。**
它检查的是「循环还满足要求吗」，不是「循环还能返回东西吗」——后者永远是 True。

---

## 八条契约，以及哪一条最容易翻车

| # | 契约 | 说明 |
|---|---|---|
| 1 | 一个 agent、一个控制循环 | thought → action → observation → repeat → final |
| 2 | 会终止 | 且不是靠撞 step cap 终止的 |
| 3 | 用了多个工具 | 至少 3 个不同工具 |
| 4 | **一轮里调用多个工具** | ← **最容易出事的一条** |
| 5 | 有 instrumentation | turns / tokens / cost / evidence / guardrails 全部记录 |
| 6 | Gate 在不可逆动作前面 | 不是在整个 agent 前面 |
| 7 | 没有框架接管循环 | 不许 LangChain / LangGraph / CrewAI / AutoGen |
| 8 | 隔离性 | 同一个 case 跑两次结果完全一致 |

**第 4 条为什么最容易翻车**：一个「能」批量调用但在你们的数据上「从不」批量调用的循环，
没有满足要求，而且 D2(c) 声称的 turn 节省根本不会出现。
`test_D1.py` 用 `tool_calls > turns` 来判定——`CLM-8842` 是 8 calls / 4 turns，过；
如果你们某次改动让它变成 8 calls / 8 turns，这条会立刻红。

**第 7 条**：脚本会扫描整个 `A2_main/` 的 import。
普通库（数据处理、HTTP、测试、绘图）完全没问题，而且是预期的。
被禁的只有**接管循环**的框架——因为循环本身就是被评分的东西。

---

## Scope boundary：这一节是防止你们浪费两周

`SCOPE_CONFIRMATIONS` 里五条全部要填 `True`。它们不是形式主义，是**每一条都不得分**：

| 不要做 | 为什么 |
|---|---|
| 信件/文档生成器 | `issue_decision_letter` 不写信，它写一行 log |
| 预约/排期应用 | 同上 |
| 任何 UI、网页、移动端 | 一分都没有 |
| PDF / Word 输出 | 一分都没有 |
| 真实发信、真实付款、写入线上系统 | **硬规则**，不是捷径 |
| 登录 / 用户账号 | 一分都没有 |

**最常见的过度建设**：把 "request a missing document" 这个 outcome 写成客户可读的正式文书。
它只需要一个短字符串：`"request: valid pre-authorisation for procedure 47120"`。
Rubric 1 里没有任何一条给措辞打分。

分数在哪里：**agent 做了什么决定、基于什么证据、经过哪个 gate、花了多少钱**，
以及能在整个评估集上证明这一点的 harness。
一个记录了正确决定和可追溯证据链的团队，分数高于一个为错误 claim 生成了漂亮信件的团队。

---

## 要写的论证

### `WHY_SINGLE_AGENT`

不要写「因为作业不让做 multi-agent」——那是 scope 规则，不是理由。要给工程理由。

可引用的证据（Pre-read 5）：Cognition 以 multi-agent 为卖点发布了 Devin，
随后自己发文更正——*Don't Build Multi-Agents*（2025-06）和
*Multi-Agents: What's Actually Working*（2026-04）。
后者的结论很有用：**review 可以扇出，写操作要保持单线程**。
我们唯一的写就是那封决策信，正好落在这个结论上。

### `ALTERNATIVE_ARCHITECTURE` —— 直接进报告第 6 节

报告第 6 节明确要求三件事，**缺一个就少分**：

1. `what_it_would_have_caught` —— 必须指名 D7 或 D4 里的**具体 case**，不能说「提高质量」
2. `what_it_would_have_cost` —— 给数字，用 D6 的价格算
3. `why_we_stayed` —— 为什么最终没做

这是明确的加分项。ILO 3 考的就是评估设计替代方案，
一段「第二个 agent 复核我们的决策记录本可以抓到失败 X，代价是 Y，我们没做是因为 Z」
正是他们想看的推理。

---

## 报告里 D1 占多少

D1 **没有自己的报告章节**。它的产出分散在：

- 第 1 节（D0）：架构定级
- 第 2 节（D2）：turn 定义和依赖规则
- 第 6 节：`ALTERNATIVE_ARCHITECTURE` 那一段，150 词

所以 D1 这里填的东西，主要服务于第 6 节和 repo 本身的可信度。
`TURN_DEFINITION` 尤其重要——它必须和 D2(c)、D6 的算术用同一个定义，
否则你们报告里的 turn 数会自相矛盾，而这是评分人最容易抓到的不一致。
