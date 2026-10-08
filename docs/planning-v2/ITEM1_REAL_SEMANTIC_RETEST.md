# Planning V2 Item 1 — Real Semantic Retest

日期：2026-10-08（Asia/Shanghai）。最终结果：**ITEM1_SEMANTIC_REVIEW_REQUIRED / ITEM2_NOT_STARTED / STOP**。

本轮五次真实请求均有明确响应，无新增unknown或截断。Case2/4/5/6程序合同与独立语义PASS；Case7模型原始内容理解正确，但来源引用违反合同，被Validator拒绝，没有有效Profile，整案FAIL。未达到Item1小规模真实语义验收通过条件，不标记ACCEPTED，不自动修复或进入Item2。

## 1. Start / Final HEAD 与修改范围

- Start HEAD：`eda8f7b3c47d64e2d9337baa246abb17fdef78d0`；Branch：`feat/n1-resource-discovery`，与指定基线完全一致。
- 开始tracked tree干净；仅既有`.workbuddy/`与`design-preview/`未跟踪目录，未访问、修改或提交。
- Final HEAD：本报告本地提交后的实际完整SHA记录于本轮最终答复及ignored `var/planning-v2-item1-retest-20261008/final-audit.json`；报告不自嵌其自身提交SHA。生产源码的最终HEAD内容仍与start HEAD相同。
- 唯一新增tracked文件：`docs/planning-v2/ITEM1_REAL_SEMANTIC_RETEST.md`。不改progress、生产代码、Prompt、Validator、Schema、frontend、migration或数据库；不push/merge/deploy。
- 权威：[Architecture Contract](PLANNING_V2_ARCHITECTURE_CONTRACT.md)；[修复报告](ITEM1_HARD_CONSTRAINT_FIX.md)；[首轮烟测](ITEM1_REAL_SEMANTIC_SMOKE.md)。原文及历史失败结论保持。

## 2. Provider、权限和真实执行

- 当前配置Provider=`openai_compatible`、官方Base URL=`https://api.deepseek.com`、请求模型=`deepseek-flash`。五次响应model均自报`deepseek-flash`；底层权重版本未由本轮独立证明。
- 既有request options：max_tokens4096、thinking.type=disabled，timeout120秒；未换Provider/模型、未改预算或购买充值。
- 重新执行origin/public DNS guard及官方非模型余额GET：HTTP200/is_available=true，余额1.97 CNY。凭据仅在进程内使用，认证头/API Key未进入日志；余额GET不计模型生成请求。
- 开始最新账本177/280、余103、历史unknown177保留；本轮追加request/result178～182，结束182/280、余98、历史unknown仍仅177。旧账本文件逐字哈希保持，unknown177没有覆盖、删除、恢复或重派。
- 本轮范围授权5、每案1、retry0/repair0。每次派发前exclusive追加账本，输入与case记录阻止重派；HTTPTransport retries=0、无redirect、trust_env=False，异常/截断会整体STOP。本轮没有需要触发unknown分支的新结果；五次额度已用尽，不另建身份补发。
- 独立入口ignored `retest.py`：现有GoalRequirementAnalyzer → RecordingPort（仅记录）→ build_llm / OpenAICompatibleLLM → DeepSeek真实HTTP。没有Fake输出、旧Planning Graph、RuntimeFactory或Worker；run_id/attempt_id仅为合成账务身份，不创建业务Run。
- 全部输入严格采用本指令的合成文本，Case2只额外设置interview，Case7只额外设置独立project_context；其余GoalSpec事实使用现有默认。Case7 target/context与旧unknown Case3均不同，身份也全新。
- 新Acceptance：`planning-v2-item1-retest-synthetic-05e04a3e09ba`；下面逐案保存独立run_id/attempt_id。

## 3. 计量、耗时与费用估算

本轮不调用外部搜索或Reader。费用估算复用同日已核对的[DeepSeek官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)快照：CNY/百万tokens，闲时cache-hit0.02、cache-miss1、output4；高峰翻倍。五次请求开始于2026-10-08北京时间13:52（UTC05:52），适用该快照的闲时估算。调用前以高峰价、估计6000输入/案和既有4096输出cap估计五案0.22384 CNY，低于可用余额；这不是精确tokenizer或新增预算。

| Case | 账本请求 | HTTP / finishReason | input / output | cache hit / miss | Provider延迟 / 入口耗时ms | 估算CNY |
|---|---|---|---|---|---|---|
| 2 | 178 | 200 / stop | 1013 / 172 | 0 / 1013 | 1564 / 1643 | 0.001701 |
| 4 | 179 | 200 / stop | 1002 / 138 | 768 / 234 | 1202 / 1282 | 0.00080136 |
| 5 | 180 | 200 / stop | 1004 / 195 | 768 / 236 | 1861 / 1943 | 0.00103136 |
| 6 | 181 | 200 / stop | 1016 / 179 | 768 / 248 | 1317 / 1395 | 0.00097936 |
| 7 | 182 | 200 / stop | 1043 / 246 | 896 / 147 | 2626 / 2711 | 0.00114892 |

实际请求尝试5、明确HTTP响应5、截断0、新unknown0。合计input=5078、output=930、total=6008；cache-hit=3200、cache-miss=1878。合计估算费用 **0.00566200 CNY**。

Provider计时合计8570ms，入口耗时合计8974ms；这些为逐案求和，不是整个任务墙钟时间。响应没有逐笔账单，Provider cost_micros=null，估算不能当实际扣款。Case7虽然业务校验失败，仍有真实usage并计入全部费用，不记作免费。历史unknown177的Token/费用仍未知，未混入本轮已知计量。

## 4. 两层验收结果

| Case | 程序合同 | 独立语义/交付 | 依据 |
|---|---|---|---|
| 2 只读Review/interview | PASS | PASS | 明确hard constraint“只读，不允许自动修改代码”，ref=goal.target；功能目标和interview保留，无扩课或机械全复制 |
| 4 必要需求推导 | PASS | PASS | PR分析、潜在问题、可追溯依据均explicit；输入已充分，不强制造inferred_required，无具体框架/写入/多Agent扩张 |
| 5 真正冲突 | PASS | PASS | 离线禁网限制与实时GitHub目标均保留，needs_clarification、一个明确问题，让用户取舍而非自行选模式 |
| 6 窄目标/免费 | PASS | PASS | JSON读写/异常处理/本地CLI/字段统计完整；免费教程约束、ready无澄清；本地JSON constraint忠实表达范围，未扩成禁网 |
| 7 已有项目 | FAIL | FAIL（原始目标理解PASS） | 三处使用未获准goal.project_context，Domain Validator拒绝；无最终Profile/完整项目事实交付，不能用原始内容正确抵消合同失败 |

Case2/4/5/6经真实Analyzer返回Profile，Schema/Enum/status/source_refs均通过现有严格Validator；对同一真实payload本地复验、反转各条source_refs顺序再验证，ID/hash/Profile相等。结构化constraints均为空，未额外伪造输入约束；自然语言完整性由独立审查判断，结构校验不证明语义真伪。structured逐字/index保护沿用有效基线离线证据，未声称五案覆盖了该分支的真实抽取质量。

Case7 HTTP/provider层返回LLMResult、finish=stop；Analyzer返回LLMFailure(goal_requirement_profile_invalid)，retryable=false、dispatch_unknown=false，保留1043/246 tokens及2626ms计量。对原始payload进行无网络Validator重放，明确得到ValidationAppError，details.field=source_refs，未修订输出或绕过校验。

原harness case-7.json保留validator=NOT RUN初始标签，但Analyzer实际上调用Validator并拒绝，因此正式结果为FAIL；case-7.validator-diagnostic.json、review-packet及本报告提供这一解释修正。原始日志未覆盖，不把无Profile误写成未请求或unknown。

### Case 2：完整输入、身份、实际输出和最终对象

- run_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-2`
- attempt_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-2:goal_requirements:1`
- 以下模型对象直接解析自保留的原始response.body，未人工修订；原content字符串同时保留于review-packet。

规范化GoalSpec：

```json
{
  "target": "我想用 Python 做一个只读的 GitHub Code Review Agent，能够分析 PR 并输出有代码依据的审查建议，不允许自动修改代码。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "interview",
  "constraints": []
}
```

模型实际content对象：

```json
{
  "schema_version": 1,
  "target_summary": "用 Python 构建一个只读的 GitHub Code Review Agent，能够分析 PR 并输出有代码依据的审查建议。",
  "required_requirements": [
    {
      "text": "用 Python 实现一个 GitHub Code Review Agent",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "能够分析 GitHub PR",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "输出有代码依据的审查建议",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    }
  ],
  "hard_constraints": [
    {
      "text": "只读，不允许自动修改代码",
      "source_refs": [
        "goal.target"
      ]
    }
  ],
  "learner_claims": [],
  "clarification_questions": [],
  "status": "ready"
}
```

最终GoalRequirementProfile（含完整三类条目、source_refs、ID及profile_hash）：

```json
{
  "clarification_questions": [],
  "desired_depth": "unspecified",
  "hard_constraints": [
    {
      "constraint_id": "constraint_e91c601abf795119f5986a42c3dda416127a153c22828f1cee5535a910d41594",
      "source_refs": [
        "goal.target"
      ],
      "text": "只读，不允许自动修改代码"
    }
  ],
  "learner_claims": [],
  "outcome_purpose": "interview",
  "project_context": null,
  "required_requirements": [
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_2a648fc7e9db66a40b38b2551067b3741f09989cd2e66110327b275d9f6cfbe4",
      "source_refs": [
        "goal.target"
      ],
      "text": "用 Python 实现一个 GitHub Code Review Agent"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_713b4734fcadafb6436910d09ed15a5c796736f5414ce6985e528cb0c6e58cb5",
      "source_refs": [
        "goal.target"
      ],
      "text": "能够分析 GitHub PR"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_931dd8e0d2743d3a9dd165e46ce2ae75436ef69f804a5b67a831d6996b60c334",
      "source_refs": [
        "goal.target"
      ],
      "text": "输出有代码依据的审查建议"
    }
  ],
  "schema_version": 1,
  "scope": [],
  "starting_point": "",
  "status": "ready",
  "target_summary": "用 Python 构建一个只读的 GitHub Code Review Agent，能够分析 PR 并输出有代码依据的审查建议。",
  "profile_hash": "f045506b60fd1443a425dc93756f1e16e4fd299aaba634b6d8d6691846f166d1"
}
```

### Case 4：完整输入、身份、实际输出和最终对象

- run_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-4`
- attempt_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-4:goal_requirements:1`
- 以下模型对象直接解析自保留的原始response.body，未人工修订；原content字符串同时保留于review-packet。

规范化GoalSpec：

```json
{
  "target": "我想实现一个能够分析 GitHub PR、识别潜在代码问题并输出可追溯审查依据的工具。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": []
}
```

模型实际content对象：

```json
{
  "schema_version": 1,
  "target_summary": "实现一个能分析 GitHub PR、识别潜在代码问题并输出可追溯审查依据的工具。",
  "required_requirements": [
    {
      "text": "分析 GitHub PR",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "识别潜在代码问题",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "输出可追溯审查依据",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    }
  ],
  "hard_constraints": [],
  "learner_claims": [],
  "clarification_questions": [],
  "status": "ready"
}
```

最终GoalRequirementProfile（含完整三类条目、source_refs、ID及profile_hash）：

```json
{
  "clarification_questions": [],
  "desired_depth": "unspecified",
  "hard_constraints": [],
  "learner_claims": [],
  "outcome_purpose": "learn",
  "project_context": null,
  "required_requirements": [
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_3686d236176f37f99189d208cbe822ce5463f7610774e739db4992eec1d44dfd",
      "source_refs": [
        "goal.target"
      ],
      "text": "分析 GitHub PR"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_5f99de52657b8ba33c74e0babc3761b985c8ad6867999b1d8c4445b7b17ee022",
      "source_refs": [
        "goal.target"
      ],
      "text": "识别潜在代码问题"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_6eeefa7b58cb29f9ee292b866c3fbb6a5fab9d812fd7c69bb68d071e74c35001",
      "source_refs": [
        "goal.target"
      ],
      "text": "输出可追溯审查依据"
    }
  ],
  "schema_version": 1,
  "scope": [],
  "starting_point": "",
  "status": "ready",
  "target_summary": "实现一个能分析 GitHub PR、识别潜在代码问题并输出可追溯审查依据的工具。",
  "profile_hash": "0753572fafb991875df873a75c7f798fc66afdfadf0f9683255bf8969ea08224"
}
```

### Case 5：完整输入、身份、实际输出和最终对象

- run_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-5`
- attempt_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-5:goal_requirements:1`
- 以下模型对象直接解析自保留的原始response.body，未人工修订；原content字符串同时保留于review-packet。

规范化GoalSpec：

```json
{
  "target": "我希望工具运行时完全离线、禁止任何网络连接，同时必须实时读取 GitHub 云端最新的 Pull Request。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": []
}
```

模型实际content对象：

```json
{
  "schema_version": 1,
  "target_summary": "让工具在完全离线、禁止任何网络连接的前提下，实时读取 GitHub 云端最新的 Pull Request",
  "required_requirements": [
    {
      "text": "工具运行时完全离线，禁止任何网络连接",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "实时读取 GitHub 云端最新的 Pull Request",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    }
  ],
  "hard_constraints": [
    {
      "text": "工具运行时完全离线、禁止任何网络连接",
      "source_refs": [
        "goal.target"
      ]
    }
  ],
  "learner_claims": [],
  "clarification_questions": [
    "工具完全离线且禁止网络连接，但又要求实时读取 GitHub 云端最新 PR，这两者存在根本冲突。你希望如何解决：是允许某种受控网络访问、接受延时同步，还是目标本身需要调整？"
  ],
  "status": "needs_clarification"
}
```

最终GoalRequirementProfile（含完整三类条目、source_refs、ID及profile_hash）：

```json
{
  "clarification_questions": [
    "工具完全离线且禁止网络连接，但又要求实时读取 GitHub 云端最新 PR，这两者存在根本冲突。你希望如何解决：是允许某种受控网络访问、接受延时同步，还是目标本身需要调整？"
  ],
  "desired_depth": "unspecified",
  "hard_constraints": [
    {
      "constraint_id": "constraint_f0125a0c2db449ca5edd62f43c688ebfc952b459594cb9cbd4f65dddeeefdfc0",
      "source_refs": [
        "goal.target"
      ],
      "text": "工具运行时完全离线、禁止任何网络连接"
    }
  ],
  "learner_claims": [],
  "outcome_purpose": "learn",
  "project_context": null,
  "required_requirements": [
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_598f17318409e8e2b50a8eb37c1d0e64173230fa6aece151075cf39b2b09b130",
      "source_refs": [
        "goal.target"
      ],
      "text": "工具运行时完全离线，禁止任何网络连接"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_f54b094de5d0ff1054cf2c5131cf1ac648d4b36eb165562306f2532daf19801a",
      "source_refs": [
        "goal.target"
      ],
      "text": "实时读取 GitHub 云端最新的 Pull Request"
    }
  ],
  "schema_version": 1,
  "scope": [],
  "starting_point": "",
  "status": "needs_clarification",
  "target_summary": "让工具在完全离线、禁止任何网络连接的前提下，实时读取 GitHub 云端最新的 Pull Request",
  "profile_hash": "07c149ab6fdb650d4ef52499d8c53ec29793ca08b3493037dd3efe9b9d9241aa"
}
```

### Case 6：完整输入、身份、实际输出和最终对象

- run_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-6`
- attempt_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-6:goal_requirements:1`
- 以下模型对象直接解析自保留的原始response.body，未人工修订；原content字符串同时保留于review-packet。

规范化GoalSpec：

```json
{
  "target": "我想学习 Python 的 JSON 文件读写和异常处理，最终写一个命令行程序，读取本地 JSON 文件并输出字段统计结果，教程要求免费。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": []
}
```

模型实际content对象：

```json
{
  "schema_version": 1,
  "target_summary": "学习 Python 的 JSON 文件读写和异常处理，并最终写一个读取本地 JSON 文件、输出字段统计结果的命令行程序，且教程必须免费。",
  "required_requirements": [
    {
      "text": "学习 Python 的 JSON 文件读写和异常处理",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "最终写一个命令行程序，读取本地 JSON 文件并输出字段统计结果",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    }
  ],
  "hard_constraints": [
    {
      "text": "教程要求免费",
      "source_refs": [
        "goal.target"
      ]
    },
    {
      "text": "程序读取本地 JSON 文件",
      "source_refs": [
        "goal.target"
      ]
    }
  ],
  "learner_claims": [],
  "clarification_questions": [],
  "status": "ready"
}
```

最终GoalRequirementProfile（含完整三类条目、source_refs、ID及profile_hash）：

```json
{
  "clarification_questions": [],
  "desired_depth": "unspecified",
  "hard_constraints": [
    {
      "constraint_id": "constraint_7e9c5619714f4a402ee967840ff2cad42b86c6d88bf9759dd863fc57ef24d5a9",
      "source_refs": [
        "goal.target"
      ],
      "text": "教程要求免费"
    },
    {
      "constraint_id": "constraint_30ce87e5d234303b179a68d98a53e8fc4c2c3cd9322efe3c9c713dda1243a574",
      "source_refs": [
        "goal.target"
      ],
      "text": "程序读取本地 JSON 文件"
    }
  ],
  "learner_claims": [],
  "outcome_purpose": "learn",
  "project_context": null,
  "required_requirements": [
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_a631a4fb43b2a8d18cab647961487e059830c74f29755efe86ecac0d6d29ada1",
      "source_refs": [
        "goal.target"
      ],
      "text": "学习 Python 的 JSON 文件读写和异常处理"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_f1a007b9bcc33d910c83a32b0e7ecd2a4311285a7b50710462b6a90eb7740236",
      "source_refs": [
        "goal.target"
      ],
      "text": "最终写一个命令行程序，读取本地 JSON 文件并输出字段统计结果"
    }
  ],
  "schema_version": 1,
  "scope": [],
  "starting_point": "",
  "status": "ready",
  "target_summary": "学习 Python 的 JSON 文件读写和异常处理，并最终写一个读取本地 JSON 文件、输出字段统计结果的命令行程序，且教程必须免费。",
  "profile_hash": "80071f1fe9050bcdad12c12d5a14dddf5a06402cbea8e247ab101dcd8bf205bb"
}
```

### Case 7：完整输入、身份、实际输出和最终对象

- run_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-7`
- attempt_id：`planning-v2-item1-retest-synthetic-05e04a3e09ba:case-7:goal_requirements:1`
- 以下模型对象直接解析自保留的原始response.body，未人工修订；原content字符串同时保留于review-packet。

规范化GoalSpec：

```json
{
  "target": "我想学习 Agent 的结构化输出和受限工具调用，并将它应用到我现有的小型待办事项管理程序中。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": [],
  "project_context": "我已经有一个本地待办事项管理 CLI，使用 JSON 文件保存任务，希望直接在现有程序上增加 Agent 能力，而不是重新创建演示项目。"
}
```

模型实际content对象：

```json
{
  "schema_version": 1,
  "target_summary": "学习 Agent 的结构化输出和受限工具调用，并将该能力应用到自己现有的本地待办事项管理 CLI 中，在原有程序上增加 Agent 能力。",
  "required_requirements": [
    {
      "text": "学习 Agent 的结构化输出",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "学习 Agent 的受限工具调用",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "将结构化输出和受限工具调用能力应用到现有小型待办事项管理程序中",
      "origin": "explicit",
      "source_refs": [
        "goal.target",
        "goal.project_context"
      ],
      "rationale": ""
    },
    {
      "text": "在现有待办事项管理 CLI 上直接增加 Agent 能力，而非重新创建演示项目",
      "origin": "explicit",
      "source_refs": [
        "goal.project_context"
      ],
      "rationale": ""
    }
  ],
  "hard_constraints": [
    {
      "text": "希望直接在现有程序上增加 Agent 能力，而不是重新创建演示项目",
      "source_refs": [
        "goal.project_context"
      ]
    }
  ],
  "learner_claims": [],
  "clarification_questions": [],
  "status": "ready"
}
```

最终Profile：**无**，hash/ID稳定性NOT RUN，未从非法输出自行制造Profile。Analyzer失败：

```json
{
  "error_class": "goal_requirement_profile_invalid",
  "message": "目标分析响应未通过结构校验",
  "retryable": false,
  "dispatch_unknown": false,
  "details": {},
  "input_tokens": 1043,
  "output_tokens": 246,
  "latency_ms": 2626
}
```

## 5. 独立审查与Case7原因

独立开发审查请求GPT-6.1 Sol medium，actual NOT OBSERVABLE；主协调请求Sol6.1 high，actual NOT OBSERVABLE。审查者不是被测DeepSeek，未调用任何产品模型，逐案对照输入、真实原始内容、Profile或失败。完整报告保留在ignored `independent-review.md`。独立结论四案PASS、一案FAIL，没有以Validator PASS替代语义判断。

Case7原始内容准确要求学习结构化输出/受限工具调用、在现有CLI上增加能力、不重建demo；没有伪称用户已会全部Agent、要求数据库/Web/cloud或扩完整todo专项。但requirements第3/4项和hard_constraints第1项共三处ref=`goal.project_context`。现有Validator唯一允许的项目背景ref是`project_context`，Prompt也列该字符串并以括号解释其指向输入goal.project_context。字段路径与ref标识的区别未被本次模型输出遵循；内部具体成因无法由响应证明。

项目背景虽仍在合成输入中，最终Profile因引用错误未生成，不能宣称project_context独立完整交付。拒绝是既有严格合同按预期工作；新缺陷是模型没有遵循canonical引用协议，不是Provider unknown、truncation或整个已有项目目标理解错误。

最小后续建议（本轮未实施）：在Item1专用Prompt中突出唯一合法项目背景ref字面值`project_context`，明确区别于输入路径`goal.project_context`，并提供专用引用示例；保留严格Validator，不静默改写响应、不新增NLP或第二模型步骤、不自动收费验证。任何后续修正需另行单项授权，不能再消费本轮身份或剩余总额度追绿。

## 6. 结束边界、未运行项目与风险

- 结束规则/Mock边界回归 **PASS，23项**，exit0。覆盖project_context不开放public generate、legacy/residual、unknown/truncation不retry、非法业务响应保留usage且不成为Profile；不将Mock测试冒充上述真实输出。
- 命令：`.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit backend/tests/unit/test_goal_requirement_input.py::test_project_context_does_not_open_public_generate backend/tests/unit/test_planning_legacy_removal.py backend/tests/unit/test_planning_residual_cleanup.py backend/tests/unit/test_goal_requirement_provider.py::test_transport_unknown_does_not_leak_or_retry backend/tests/unit/test_goal_requirement_provider.py::test_known_response_failures_do_not_retry_or_repair backend/tests/unit/test_goal_requirement_analysis.py::test_invalid_business_response_is_known_failure_with_usage_not_authority -q --junitxml=var/planning-v2-item1-retest-20261008/boundary.xml`。
- 502份既有backend/frontend/contracts/架构/实施与失败报告/progress/.env文件哈希全部保持，旧账本文件哈希全部保持。没有生产、Prompt、Schema、migration或占位页改动。
- 公共generate仍scope后503；未注册Fake Planning、启动旧Graph/Worker或开放公开入口。新Planning Run0/Job0/Draft或Plan mutation0/DB写入0，依据为独立入口没有DB/Repository接线和fail-closed spy/HTTP门禁，**不是真实PG行计数**。
- 产品搜索0、外部搜索0、Reader0、其他产品模型0；未新建凭据、充值或提升cap。五案全部新身份，Case7为全新合成项目，不是unknown Case3重派。
- 真实PG/checkpoint及行数验证NOT RUN；全backend执行/collection、frontend build、浏览器、完整PlanningV2端到端NOT RUN。复用刚完成修复基线的198回归/2061collection证据，未声称本轮重复运行。
- 大规模语义质量、稳定性、多次采样和真实用户项目质量NOT RUN；Case4全为explicit，因此本轮未观察到真实inferred_required及rationale质量。精确费用账单未提供，费用仅估算。
- 失败输出、raw body、input/request身份、Provider结果、四个Profile、case7诊断、计量和独立审查均保留于ignored `var/planning-v2-item1-retest-20261008/`；STOP文件保留，五次授权已用完，不补发。API Key及认证头没有写入证据。
- 恢复检查点：ignored `var/codex-goals/planning-v2-item1-real-semantic-retest.json`。仅本报告本地提交，提交前后git diff --check核对；不push/merge/deploy。

## 7. Item1验收与Item2建议

**未达成ITEM1_REAL_SEMANTIC_ACCEPTED。** 五案均明确完成请求，因此不是因unknown或NOT RUN而不完整；但Case7是关键合同FAIL，按本轮规则选择 **ITEM1_SEMANTIC_REVIEW_REQUIRED**。修复后的只读Case2本次代表验证PASS，不将其扩大为整个Item1通过。

**不建议进入Item2，且未启动。** 应先单独评审项目背景canonical source_ref问题；本轮不实施建议、不重新收费，不把全产品标记READY。完整PlanningV2仍STAGING_BLOCKED / NOT_READY。

**ITEM1_SEMANTIC_REVIEW_REQUIRED**

**ITEM2_NOT_STARTED**

**STOP**
