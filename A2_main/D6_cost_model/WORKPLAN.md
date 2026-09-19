# D6 · 成本模型 —— 工作内容

> 用 Class 5 的三层模型。**用 D4 实测的 success rate 和 D5 实测的 token 数，不是估计值。**
>
> **评分标准**：*"This is marked on METHOD, not on arithmetic precision.
> A defensible model with stated assumptions, three separated layers, a sensitivity
> range and four measured levers beats a confident single number with none of them."*
>
> 报告第 4 节 400 词。它比往年大，因为成本模型现在有**四个实测杠杆**和**一个要辩护的区间**。

---

## 这个文件夹里有什么

| 文件 | 是什么 | 你要动吗 |
|---|---|---|
| `answers_D6.py` | **用户工作文件**：价格、人工成本、量、四杠杆 | **要** |
| `cost_model.py` | 三层 + 敏感度 + 盈亏平衡点的纯函数 | 不用 |
| `levers.py` | 拼装报告第 4 节，自动拉取 D2/D4/D5 的实测数 | 不用 |
| `test_D6.py` | **用 brief 自己的算例做单元测试** | 不用 |

```bash
python A2_main/D6_cost_model/test_D6.py     # 含算术单元测试
python A2_main/D6_cost_model/levers.py      # 完整报告第 4 节
```

`test_D6.py` 已经验证过公式能复现 brief 的两个算例（91.2% 和 86.2%）。
**如果你们改了 `cost_model.py` 而这两条红了，说明改坏了。**

---

## 三层，以及为什么要分开

| 层 | 是什么 | 规模变大时 |
|---|---|---|
| 1 · per-task variable | input + output token + 工具费 | **线性。永不摊薄** |
| 2 · per-task expected fallback | `(1 − success_rate) × 一次失败的成本` | **线性。永不摊薄。通常是最大的一层，也是几乎所有成本模型都漏掉的那一层** |
| 3 · fixed monthly | 存储、基础设施、**你们自己的 eval 运行**、监控、维护 | 每 task 成本永远在降 |

**Layer 2 就是 D4 的 pass rate 落地的地方。**
一个一半时间在犯错的便宜 agent 不便宜——所以第 4 个杠杆就是 success rate 本身。

### Baseline 规则

**只放 input/output token 的 list price，不要放任何更聪明的东西。**
prompt caching（压低账单）和 reasoning model（推高账单）都是真的，
但它们**依模型而异**，放进 baseline 会让你们的头条数字无法被核对。

先报 baseline，**再把调整后的数字并排放**，说明改了什么。

---

## Layer 2 用人工成本算，不要猜

```
failure_cost = 时薪 × 每次升级的分钟数 ÷ 60
```

> *"A failure is not free just because no human is named in the design."*

Appendix A 给了每个问题默认的角色和处理时长。用它，或者换成你们自己的**并说明为什么**。
Problem A 的 worked example 用的是 **US$7.60 一次**（claims assessor，US$38/小时，12 分钟）。

---

## 盈亏平衡点：真正决定你们上哪个模型的那个问题

```
break_even = 1 − (E − C) / F
```

| 量 | 是什么 | 从哪来 |
|---|---|---|
| `C` | 便宜模型跑**一次**的成本 —— **只算 token** | 你们的 token 数 × 价格 |
| `E` | 贵模型一次成功 task 的成本 —— **它自己的 layer 1 + layer 2** | D5 的实测 |
| `F` | 一次失败的成本 —— 那次升级 | 上面算出来的 |

**一句话逻辑**：换成便宜模型，每个 task 省下 `E − C`。一次失败花 `F`。
所以在把省下的钱赔光之前，你能承受的失败次数是 `(E − C) ÷ F`，剩下的就是需要的成功率。

### 为什么 E 含它自己的失败而 C 不含

贵模型你**测过**它的成功率，所以能给它的失败定价并折进去。
便宜模型的成功率**正是你要解的未知数**，所以它不能出现在等式那一边。
这个不对称就是公式看起来别扭的全部原因。

> ⚠️ **一个容易错的细节**：brief 把 `E` 叫 "cost per successful task"，
> 但紧接着定义它是 "layer 1 + layer 2 for that model"——**没有再除以成功率**。
> 两种算法差 0.5 个百分点（91.4% vs 90.7%），够接近到看起来对、够远到丢分。
> `cost_model.expensive_model_E()` 按 brief 的**定义**实现，docstring 里写明了这一点。
> 建议在报告里也点一句你们用的是哪个。

### 读出它的含义

brief 的算例：便宜模型 US$0.005、贵模型 US$0.049、贵模型实测 92%、失败成本 US$7.60
→ **盈亏平衡点 91.2%**。

便宜模型**便宜十倍**，却仍然必须落在贵模型**一个百分点以内**才值得选。
**当失败很贵时，模型价格几乎不重要，准确度才重要。**

反过来也成立：失败成本降到 US$0.76，平衡点掉到 86.2%——
便宜模型能承受约 14% 的失败而不是 9%。
**错得越便宜，token 价格越重要。**

`BREAK_EVEN_READING` 要用你们**自己的两个实测数字**写一句话。
brief 说这是报告里最有用的一句话。

---

## 成本账本：四个杠杆 —— 这部分扣分最狠

> *"A cost model that only reports a number tells us nothing about your design.
> Report the four levers you pulled, with a measured before and after for each."*

| # | 攻击什么 | 在哪建的 | 报什么 |
|---|---|---|---|
| 1 | **B** —— 工具块，每轮重发，调不调用都发 | D2(a) 剪工具 | 剪前/剪后的 tool definition token 数 |
| 2 | **T** —— 轮数，**二次项，你手上最大的杠杆** | D2(c) 并行调用 | 串行 vs 并行的轮数和 input token |
| 3 | **D** —— 观察值大小，**复合**（每个观察在之后每轮都被重发） | D2(b) 描述符重写 | v1 vs v2 每次调用返回的 token |
| 4 | success rate —— 设定 layer 2 | D4 评估集 | 实测 pass rate 和它推出的每成功 task 成本 |

**杠杆 1 和 3 看起来像，其实不是**：
胖工具块是轮数的**线性**函数；胖观察值**复合**。两个都值得砍，**但只有一个会爆炸**。
`DOMINANT_LEVER` 要说清哪个主导了你们的账单**以及怎么知道的**。

好消息：`levers.py` 会**自动从 `output/` 拉取**这四个杠杆的实测数字——
杠杆 2 已经有了（串行 8 轮 / 59,400 token vs 并行 4 轮 / 21,000 token）。
你们只需要填 `before`/`after`/`note` 的文字说明。

---

## 敏感度：给区间，不给点估计

你们的 success rate 是估计，failure cost 也是。
所以要给出 **success rate ± 10 个百分点**范围内的每成功 task 成本，
并说明**你们的结论在整个区间内是否成立**。

> *"A robust answer and a knife-edge answer deserve different amounts of confidence,
> and a sponsor is entitled to know which one you are handing them."*

`levers.py` 会自动打这张表并算出跨度百分比。

---

## 三个 cap 要和成本模型一起陈述

`step cap` · `budget ceiling` · `monthly limit per user`

前两个在 `config.py` 里并由 `Guardrails` enforce，`test_D6.py` 会检查
`answers_D6.CAPS` 和它们一致。
**第三个**（`MONTHLY_LIMIT_PER_USER`）定为**政策承诺**：在
`answers_D6.CAPS` / 报告里陈述数值与单位，并写明它不是代码控制——
不在 `Guardrails` 里 enforce（单次运行看不到跨 run 的月度用量）。

---

## 报告第 4 节结构建议（400 词）

| 段 | 内容 | 词数 |
|---|---|---|
| 1 | 三层各是多少 + **layer 2 是 layer 1 的几倍**（这个比值最有说服力） | 80 |
| 2 | 你们问题量级下的月度总额 + 每成功 task 成本 | 60 |
| 3 | 四个杠杆各一句 before/after，**点名哪个主导** | 120 |
| 4 | 敏感度区间 + 结论是否在全区间成立 | 60 |
| 5 | 盈亏平衡点 + 那句带两个实测数字的话 | 60 |
| 6 | 三个 cap；caching / reasoning 如果适用在这里提 | 20 |

表格放 repo：三层表、敏感度表、四杠杆账本。`levers.py` 打出来的直接可用。
