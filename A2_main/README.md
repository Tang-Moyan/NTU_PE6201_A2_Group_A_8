# A2_main · Problem A 的完整解决方案

PE6201 A2，Problem A（health-insurance claim first response）。

**`A2_main` 就是提交物本身。** 它带着 agent、工具层、护栏、harness、backend 和 fixture 数据，
可以独立运行——不读旁边那两个文件夹。

`A2_scaffold/` 和 `A2_reference_data/` 是**原始参考件**，
想知道自己改了什么就去 diff 它们，**运行时不会碰它们**。

---

## 四条命令

```bash
python A2_main/run_eval.py            # 评分人跑的那条
python A2_main/run_all.py             # 产出全部数字（免费、离线）
python A2_main/test_all.py            # 还有什么要「决定」
python A2_main/code_todo.py           # 还有什么要「写」
```

后两条是配套的，报的是**两种不同的待办**：

| | 是什么 | 放在哪 | 怎么找到 |
|---|---|---|---|
| `TEMPLATE(...)` | 一个**决策**或一段**文字** | `answers_Dx.py` | `test_all.py` |
| `TODO(D3/gate)` | 一段**代码** | 实现文件里那一行上 | `code_todo.py` |

两个都读自源码，所以**都不会过期**。也可以直接 grep：

```bash
grep -rn "TODO(D" A2_main
```

---

## 代码在哪：每个交付物拥有它被评分的那部分

这样「D3 还差什么代码」是一个**文件夹**，而不是一次全局搜索。

```
A2_main/
├── run_eval.py                   ← 评分人的入口
├── config.py                     vendor-neutral 块 + 护栏限制值      D5/D3
├── data/                         fixture、答案键、生成器、校验器      D4
│   ├── data_A/*.json
│   ├── expected_outcomes_A.json
│   ├── make_fixtures_A.py
│   └── check_my_data.py
│
├── D1_agent_loop/
│   ├── agent.py                  ★ ReAct 循环本体
│   ├── loop_contract.py          八条契约的验证
│   └── answers_D1.py  test_D1.py  WORKPLAN.md
│
├── D2_tool_layer/
│   ├── tools.py                  ★ 七个工具的实现 + 六字段描述符
│   ├── prompt.py                 ★ 描述符 → system prompt
│   ├── tool_audit.py             D2(a) 三问评分 + 工具块 token
│   ├── descriptor_ab.py          D2(b) v1 vs v2
│   ├── parallel_ab.py            D2(c) 串行 vs 并行
│   └── answers_D2.py  test_D2.py  WORKPLAN.md
│
├── D3_guardrails/
│   ├── guardrails.py             ★ step cap / budget / dedup / gate
│   ├── checklist.py              六个触发器，跑 10 条护栏用例
│   └── answers_D3.py  test_D3.py  WORKPLAN.md
│
├── D4_eval_set/
│   ├── harness.py                ★ 评分器 + 判断队列
│   ├── scripts.py                ★ 逐案例的脚本动作
│   ├── eval_runner.py            跑评估集，写 P 和 turn 分布
│   ├── sync_fixtures.py          新案例 → 生成器 + 答案键
│   └── answers_D4.py  test_D4.py  WORKPLAN.md
│
├── D5_model_battery/
│   ├── backends.py               ★ scripted / live 两个 backend
│   ├── battery.py                D5(a) 复现 + D5(b) 三模型对比
│   └── answers_D5.py  test_D5.py  WORKPLAN.md
│
├── D0_why_an_agent/              梯子、两个测试、s = P^(1/T)
├── D6_cost_model/                三层、四杠杆、敏感度、盈亏平衡点
├── D7_failures/                  两个「删除式」失败复现
├── report/                       六节拼装 + 字数
├── common/                       TEMPLATE 哨兵、codemap、路径、结果存储
└── output/                       所有实测数字（JSON）
```

★ = 需要你们读懂并可能改写的实现文件。`python A2_main/code_todo.py --files` 会列出这张表。

---

## 每个 D 文件夹的四件套

| 文件 | 是什么 |
|---|---|
| `WORKPLAN.md` | **先读这个。** 要做什么、怎么做、报告里怎么写 |
| `answers_Dx.py` | **决策与文字**都填在这里，TEMPLATE 集中 |
| 实现 + 测量 `.py` | 代码。要写的地方有 `TODO(Dn/topic)` 标记 |
| `test_Dx.py` | 进度自查 + 一致性检查 |

---

## TEMPLATE 怎么用

```python
RUNG = TEMPLATE("问题落在第几级？填 1-7 的整数", example=7)   # 填之前
RUNG = 7                                                      # 填之后
```

**把整个 `TEMPLATE(...)` 调用替换掉，不要保留外壳。**

它是**假值**、打印成 `«TODO: ...»`、并且**拒绝参与算术**——
一个悄悄变成 0 的缺失数字会产出一个自信而错误的成本模型，
而那正是这份作业整个围绕着要你们注意的失败。

`hint` 是中文，只给你们看；**填进去的值一律用英文写**，因为它们会进报告。

---

## 数字怎么在 D 之间流动

各个 D 互相读对方的测量结果，全部经由 `output/*.json`。
这不是为了好看：**六个人手工传这些数字，就是报告里出现三个不同 pass rate 的原因。**

```
D4 eval_runner  ──► P（pass rate）、turn 分布 ──┬──► D0 的算术
D7 failure_runs ──► T（median turns）───────────┤    └──► D3 的 cap 论证
D2 tool_audit   ──► lever 1（工具块 token）  ─┐ │
D2 parallel_ab  ──► lever 2（轮数、input token）├─┴──► D6 的成本账本
D2 descriptor_ab──► lever 3（返回值 token）  ─┤
D4 eval_runner  ──► lever 4（success rate）  ─┘
D5 battery      ──► 每个模型的成本 ───────────► D6 的盈亏平衡点
```

`run_all.py` **按依赖顺序**跑，不是按字母顺序。
D0 虽然是第一个写的，却是**最后一个跑的**——`s = P^(1/T)` 需要 harness 跑完才有数。
先写 D0 的论证、最后测量它，是预期的顺序，不是脚本的意外。

---

## test_all.py 的三个状态，含义不同

| 退出码 | 含义 |
|---|---|
| `0` | 完成且已验证 |
| `1` | 没坏，还有活没干（**早期的正常状态**） |
| `2` | **有东西是错的，不只是没写** |

**先看 2。** FAIL 表示框架抓到了一个**矛盾**：
报告里辩护的 cap 和 `config.py` 里跑的不一致、脚本违反了你们自己的依赖规则、
某个 deletion 加回去恢复不了原状。**每一条评分人也会注意到。**

---

## 现在已经能跑出来的真实数字

不用填任何东西，`run_all.py` 已经产出：

| 发现 | 数字 | 在哪 |
|---|---|---|
| 并行 vs 串行 | 4 轮 / 21,000 token **vs** 8 轮 / 59,400 token | D2(c) |
| **串行撞破预算上限** | 60,480 > 60,000，结论从 approve 变成 escalate | D2(c) |
| Loop failure 复现 | 4→6 轮、1.8 倍 token、**答案仍然正确、不报错** | D7 |
| 循环契约 | 8 条全过（含「一轮多调用」） | D1 |
| Vendor 中立性 | 网络调用只有一处：`D5_model_battery/backends.py` | D5 |

这些可以直接进报告——**它们是实测的，不是估计的。**

---

## 从哪开始

### 今天就做的一件事

`answers_D0.py` 里的 `GOOD_RUN_STATEMENTS`（五条「什么算一次好运行」），
**单独 commit 一次**。它必须在第一个 agent commit 之前提交，评分人会看 commit history。

```bash
git add A2_main/D0_why_an_agent/answers_D0.py
git commit -m "D0(c): what a good run looks like, before any agent code"
```

### 代码的顺序（`code_todo.py` 也会提示）

1. **`D4_eval_set/scripts.py`** —— 还差 39 个脚本。
   D3 的敌意文本用例、D5(a) 的可复现运行、D0 的「步骤数随输入变化」全都卡在这上面
2. **`D5_model_battery/backends.py`** —— 真实 token 计数，必须在跑 live battery 之前写好，
   否则 D6 的 layer 1 是一个贴着「measured」标签的估计值
3. **`D3_guardrails/guardrails.py`** —— 敌意文本的防御放在哪一层
4. **`config.py`** —— 三个 cap，等 D7 打印出 turn 分布之后再定值

### 文字的顺序

D4（案例最多）→ D2（报告第 2 节最大）→ D7 → D3/D6 → D5 live → D0/report

---

## 和参考件的关系

```bash
# 想知道自己改了什么
diff A2_main/D2_tool_layer/tools.py A2_scaffold/tools.py
diff -r A2_main/data/data_A A2_reference_data/data_A
```

**注意**：`A2_reference_data/check_my_data.py` 存了每一行 shipped 数据的指纹。
`A2_main/data/` 里的副本也带着同样的指纹，所以**改了 shipped 行会被抓出来**——
这是有意的，那些行是评分人重跑你们 harness 时的基准。**只加新 id，绝不改旧行。**
