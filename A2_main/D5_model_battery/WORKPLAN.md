# D5 · 模型矩阵 —— 工作内容

> 同一个 harness 跑两次。**这一步让 harness 从「一张表格」变成「一台仪器」。**
>
> **D5(a)** scripted run —— 确定性、无网络、无 key，评分人 clone 下来就能复现你们的数字
> **D5(b)** live battery —— 至少三个模型，通过 OpenRouter

---

## 这个文件夹里有什么

| 文件 | 是什么 | 你要动吗 |
|---|---|---|
| `backends.py` | **★ scripted / live 两个 backend**。唯一知道 vendor 的地方 | usage 已接好 |
| `answers_D5.py` | **用户工作文件**：模型清单 + 价格 + 分歧解读 | **要** |
| `battery.py` | 跑 scripted / live；`A2_OWNER` 时写分片 | 不用 |
| `merge_battery.py` | 把各人的 `D5_battery_<Owner>.json` 合成总表 | 不用 |
| `test_D5.py` | 检查可复现性 + **vendor 中立性**（读源码） | 不用 |

vendor-neutral 的三个字符串在 `A2_main/config.py`；
逐案例的脚本动作在 `A2_main/D4_eval_set/scripts.py`（脚本属于**案例**，不属于 vendor）。

```bash
python A2_main/D5_model_battery/test_D5.py       # 免费
python A2_main/D5_model_battery/battery.py       # 免费，scripted
# 每人只跑自己的模型（写 output/D5_battery_<Owner>.json，不覆盖别人）：
$env:A2_LIVE=1; $env:A2_OWNER="Jojo"; $env:OPENROUTER_API_KEY="sk-or-..."
python A2_main/D5_model_battery/battery.py
# 全员推完分片后，合并成 D6 / 报告读的总表：
python A2_main/D5_model_battery/merge_battery.py
```

---

## D5(a)：这一条失败会直接封顶 Technical Execution

> *"BACKEND = "scripted" must be the default in the submitted code.
> If it does not run this way, Technical Execution is capped."*

`test_D5.py` 是**读 `config.py` 的文本**来检查这一条的，不是 import 它——
因为评分人拿到的是**提交的内容**，不是你们 shell 里的环境变量。

`FRESH_CLONE_TESTED` 要写日期和人。真的去做：
把自己的仓库 clone 到一个全新目录，在**没有 key** 的机器上跑 `python run_eval.py`。
*"works on my laptop" has caught out every cohort so far.*

---

## D5(b)：报什么，不报什么

**不是**「哪个模型最好」。是：

> **哪个模型能以什么代价干你们这份活，以及它们在哪里分歧。**
> *Expect them to diverge most on the negative cases; that is the finding to look for.*

所以 `battery.py` 把 **negative-only pass rate 单独报出来**——
总 pass rate 会把这个分歧藏起来，negative pass rate 不会。

`DIVERGENCE_FINDING` 要具体到 case_id 和 family。反例：

> ❌「便宜模型表现较差」
> ✅「三个模型在 31 个普通 case 上完全一致。分歧全在 prompt injection：
> 便宜模型在 CLM-8952 的伪装工具输出上 3 次里跟了 2 次，另两个模型每次都升级。」

---

## 预算与分工

brief 给的形状：

```
完整评估集 × 1 trial × 3 个模型
  +  negative-only × 3 trials × 3 个模型
```

**按人分模型：一人负责一个模型，用自己的 key 跑。**
6–7 人的话还能再加第四个。`answers_D5.MODELS` 里的 `owner` 字段就是记这个的。

`battery.py` 在没有 `A2_LIVE=1` 时**拒绝**跑 live，也拒绝在模型少于三个时启动。

---

## Vendor 中立性：一个字符串就能换模型

要求是：一个 `BACKEND` / `MODEL` / `BASE_URL` 块，**且只有一个函数知道有 vendor 存在**。

`test_D5.py` 会扫描整个 `A2_main/` 里所有网络调用，超过一处就报错。
现在它只定位到 `D5_model_battery/backends.py` 里的 `_live_call`，通过。

**如果你们改了 backends.py，重跑这个检查。** 把 `requests.post` 撒到三个文件里，
这一条就废了，而这是 D5 明确要求的。

---

## 一个容易被漏掉的坑：live backend 返回零 token

`backends.py` 里的 `LiveBackend.token_estimate()` **故意返回 0** ——
这就是 `TODO(D5/tokens)` 标记的那一处。

```python
@staticmethod
def token_estimate(transcript):
    # TODO(D5/tokens): return the REAL usage numbers.
    return 0, 0
```

API 每次都会把它们送回来：`payload["usage"]["prompt_tokens"]` 和
`payload["usage"]["completion_tokens"]`。
`_live_call()` 目前把整个 payload 除了 message content 以外全都丢掉了——
在那里把 usage 捞出来，存到实例上，再从这里返回。

**在 reasoning model 上，thinking token 已经算在 `completion_tokens` 里了，
这是你唯一能注意到它们的途径。**

**跑 live battery 之前必须把 API 返回的 usage 块接进去**，
否则 D6 的 layer 1 就是一个贴着「measured」标签的估计值——
而这正是 D6 明确要扣分的事情。

`battery.py` 检测到 live 运行报了零 token 会直接报错提醒。

---

## 两个可选项（都不推荐，但用了就要说清）

### Reasoning model —— 把账单**推高**

thinking token 按 **output** 计费，而 output 在便宜档是 input 的 4 倍、frontier 档 5 倍。
一个悄悄吐 900 个 thinking token 的模型（对比普通模型的 100 个）
**不是「贵一点」，它把账单的形状改了。**

怎么看出来：读 API 返回的 usage 块，不要读你自己的估计。
OpenRouter 的 `reasoning` 对象里，`effort` 是比例而非绝对值：
大致 `minimal` 10% / `low` 20% / `medium` 50% / `high` 80%；
Anthropic 的 `max_tokens` 下限是 1024。

> **brief 的建议：别用。** 分数在 harness 里，reasoning token 会很快吃光 US$10 的 key。
> 用了就必须 cap，说明 cap 到多少，**并且两种方式都报成本**——那个对比本身就是个好发现。

### Prompt caching —— 把账单**压低**

**不要建模，要实测。** 机制、折扣、计费方式因 vendor 和模型而异，而且会变：
有的自动缓存、有的要你标记块、有的先收一笔写入费才开始省、有的几分钟就过期。

最容易踩的坑：**cache 只在 prefix 完全不变时命中**。
在 system prompt 顶上放一个时间戳，就等于悄悄关掉了 caching 而你不会发现。

做法：同一个评估集开/关各跑一次，token 数**从 API 响应取**，两个都报。

---

## 报告位置

D5 和 D4 合用**第 3 节（350 词）**，见 D4 的 WORKPLAN 里的结构建议。
模型对比表放 repo，正文只写分歧结论和「我们上哪个模型」。

`WHICH_MODEL_WE_SHIP` 的结论**必须和 D6 的盈亏平衡点一致**。
脚本不检查这个，但评分人会读出矛盾。
