# Planning V2 Item 1 — 真实模型语义烟测与独立验收

日期：2026-10-08（Asia/Shanghai）。结果：**ITEM1_SEMANTIC_REVIEW_REQUIRED / ITEM2_NOT_STARTED / STOP**。

本轮未修改生产代码、Prompt、Schema 或数据库。Case 2 已观察到硬约束分类缺陷；Case 3 transport unknown 后停止，后续三例未派发。未达到六案均通过的门槛，不自动进入 Item 2。

## 1. 基线、授权和调用入口

- Start HEAD：`9c63e634b61db3cc4e472f09e3e9107ada75b1cf`；Branch：`feat/n1-resource-discovery`，与预期一致。
- 开始 tracked tree 干净；仅既有 `.workbuddy/`、`design-preview/` 未跟踪目录，未访问、修改或提交。
- 架构权威：[Architecture Contract](PLANNING_V2_ARCHITECTURE_CONTRACT.md)；实现基线：[Item 1 报告](ITEM1_GOAL_REQUIREMENT_ANALYSIS.md)。两份原文保持。
- 用户本轮明确授权当前产品 Provider 最多6次、每案一次。沿既有 append-only 账本新增范围授权，累计 cap280不变；历史174对 request/result及其他账本原文件哈希保持。
- 调用入口为 ignored `var/planning-v2-item1-real-20261008/smoke.py`：现有 `GoalRequirementAnalyzer → RecordingPort（只记录）→ build_llm / OpenAICompatibleLLM → 官方HTTP`。未调用旧Graph/RuntimeFactory/Worker，不创建业务Run/Job或任何PG记录。
- HTTPTransport retries=0、禁止redirect、trust_env=False；每次派发前exclusive写入request，case文件与账本阻止重派；unknown后STOP文件拒绝所有后续案例。
- 所有输入为本指令给定的合成文本。仅Case2设置interview、Case3设置project_context，其余使用GoalSpec默认事实；不预先替模型抽取约束或Python声明。

## 2. Provider、权限、预算和计量

- 配置Provider=`openai_compatible`，Base URL=`https://api.deepseek.com`，请求模型=`deepseek-flash`；两个真实响应model字段也为`deepseek-flash`。底层权重版本未由响应独立证明。
- 既有request options：max_tokens4096、thinking.disabled；timeout120秒。配置/模型/预算无修改。endpoint origin/public DNS guard PASS。
- 以现有凭据调用非模型账户余额接口，HTTP200/is_available=true，余额1.97 CNY。认证头、密钥、Cookie均未写入证据；没有创建新凭据。账户余额GET不计模型生成请求。
- 开始账本174/280，余106、历史unknown0。本轮尝试3次后177/280，余103，其中新增unknown1；unknown仍占用一笔，不从账本删除。范围剩余3次未使用，STOP后不自动消费。
- 开始费用检查采用[DeepSeek官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：CNY/百万tokens，闲时cache-hit0.02/cache-miss1/output4，高峰翻倍。本轮两次已响应请求发生于北京时间13:26～13:27，按闲时估算。
- 调用前按每案估计6000输入、既有4096输出上限及高峰价格估计六案0.268608 CNY，低于可用余额；输入估计不冒充精确tokenizer或新增预算。管理侧网页价格核对与产品Resource Search分开记录，产品搜索/Reader0。
- 响应未提供精确费用，Provider cost_micros=null；下表费用仅由实报usage及官方价推算，不能当逐笔账单。Case3 Token/费用/finishReason均未知，整体实际总费用未知。

| 案例 | HTTP / Provider | 输入 / 输出 tokens | cache hit / miss | Provider延迟 / 入口耗时ms | finishReason | 估计CNY（非账单） |
|---|---|---|---|---|---|---|
| 1 | 200 / LLMResult | 788 / 133 | 0 / 788 | 4331 / 4417 | stop | 0.00132000 |
| 2 | 200 / LLMResult | 798 / 195 | 512 / 286 | 1906 / 2037 | stop | 0.00107624 |
| 3 | 无响应 / LLMFailure unknown | 未知 / 未知 | 未知 | 5334 / 5432 | 未知 | 未知，不记0 |
| 4～6 | NOT RUN | — | — | — | — | — |

已知响应合计input=1586、output=328、total=1914；闲时估计费用0.00239624 CNY。包含未知请求的整体费用无法计算。三次入口耗时合计11886ms、Provider计时合计11571ms；不把它当全任务墙钟时间。

## 3. 六案结构和语义验收

| Case | 执行 | 程序合同 | 独立语义 | 结论依据 |
|---|---|---|---|---|
| 1 | 真实响应 | PASS | PASS | Python进入learner_claims；没有Python复习或MCP/RAG/LangGraph扩展；目标正确 |
| 2 | 真实响应 | PASS | FAIL | Code Review/Python/interview/只读文字保留；但hard_constraints为空，未完成明确限制分类 |
| 3 | unknown后STOP | Profile校验NOT RUN；失败传播PASS | AMBIGUOUS | ConnectError，无输出，不猜语义/计费/远端是否接收 |
| 4 | NOT RUN | NOT RUN | AMBIGUOUS | 未验证必要推断、origin/rationale |
| 5 | NOT RUN | NOT RUN | AMBIGUOUS | 未验证冲突识别与澄清 |
| 6 | NOT RUN | NOT RUN | AMBIGUOUS | 未验证窄目标ready与免费限制 |

Case1/2均由真实Analyzer返回Profile。严格Validator已检查字段/Enum/source membership/状态一致性；本地对同一真实payload复验，并反转各source_refs顺序后比较，Profile及ID/hash完全一致。稳定性指同一输入输出的确定性，不证明不同模型采样语义稳定。

Case3为provider_transport_unknown，dispatch_unknown=true、retryable=false，Analyzer原样返回同一失败类型，无重试/repair。原始harness case-3.json的validator=FAIL是整体失败初始标签，Domain Validator实际上未收到输出，正式结构结果为NOT RUN；原始文件未覆盖，review-packet与本报告明确纠正该解释。

### Case 1：合成输入与实际结果

规范化Goal输入：

```json
{
  "target": "我已经会 Python，想系统学习 Agent 开发，最终能够独立开发一个小型 Agent 应用。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": []
}
```

实际模型content解析对象（完整七字段，无人工修订）：

```json
{
  "schema_version": 1,
  "target_summary": "用户已会Python，希望系统学习Agent开发，最终能独立开发一个小型Agent应用。",
  "required_requirements": [
    {
      "text": "系统学习Agent开发的相关知识",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "具备独立开发小型Agent应用的能力",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    }
  ],
  "hard_constraints": [],
  "learner_claims": [
    {
      "text": "已经会Python",
      "source_refs": [
        "goal.target"
      ]
    }
  ],
  "clarification_questions": [],
  "status": "ready"
}
```

最终validated GoalRequirementProfile（完整source_refs、identity、hash）：

```json
{
  "clarification_questions": [],
  "desired_depth": "unspecified",
  "hard_constraints": [],
  "learner_claims": [
    {
      "claim_id": "claim_749355a0bec5c84c81572ea0c919e8dd8c4de09fdc8b9ac83d088a5e566be7c9",
      "source_refs": [
        "goal.target"
      ],
      "text": "已经会Python"
    }
  ],
  "outcome_purpose": "learn",
  "project_context": null,
  "required_requirements": [
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_12a821ac5773b60bd16cf6a2c52f2d055754b60c98e47837dbb130d09eee5846",
      "source_refs": [
        "goal.target"
      ],
      "text": "系统学习Agent开发的相关知识"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_ec34724ccd424f97ef7d9207d9e33114314503abeb84c1655ca9696cc021bcbd",
      "source_refs": [
        "goal.target"
      ],
      "text": "具备独立开发小型Agent应用的能力"
    }
  ],
  "schema_version": 1,
  "scope": [],
  "starting_point": "",
  "status": "ready",
  "target_summary": "用户已会Python，希望系统学习Agent开发，最终能独立开发一个小型Agent应用。",
  "profile_hash": "74230641efee17cfd1b1aa6db4a5e9dba4c51760820123626ca0439bbefc4b8e"
}
```

### Case 2：合成输入与实际结果

规范化Goal输入：

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

实际模型content解析对象（完整七字段，无人工修订）：

```json
{
  "schema_version": 1,
  "target_summary": "用Python实现一个只读的GitHub Code Review Agent，能分析PR并输出有代码依据的审查建议，不自动修改代码。",
  "required_requirements": [
    {
      "text": "实现一个用于分析和审查GitHub Pull Request的Agent",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "该Agent必须使用Python实现",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "Agent只能以只读方式工作，不得自动修改代码",
      "origin": "explicit",
      "source_refs": [
        "goal.target"
      ],
      "rationale": ""
    },
    {
      "text": "输出包含代码依据的审查建议",
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

最终validated GoalRequirementProfile（完整source_refs、identity、hash）：

```json
{
  "clarification_questions": [],
  "desired_depth": "unspecified",
  "hard_constraints": [],
  "learner_claims": [],
  "outcome_purpose": "interview",
  "project_context": null,
  "required_requirements": [
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_6a8ee5b59175c18d2d8a473d332a714aa5f34df4ac243212cb8fcec01f730b2d",
      "source_refs": [
        "goal.target"
      ],
      "text": "实现一个用于分析和审查GitHub Pull Request的Agent"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_c2b0ca4d79bc5971234fb59e3d958a3251159937d93c8f39a8e22d7ae464e3cd",
      "source_refs": [
        "goal.target"
      ],
      "text": "该Agent必须使用Python实现"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_92ef6d2f6a5c312ce20a4bed9d338d9b64575c3668b246e39d9162b902c9a335",
      "source_refs": [
        "goal.target"
      ],
      "text": "Agent只能以只读方式工作，不得自动修改代码"
    },
    {
      "origin": "explicit",
      "rationale": "",
      "requirement_id": "req_721a794df4d80565c2561fa42a1a7306d5c63e181934bd14984c5dc95bf2cc55",
      "source_refs": [
        "goal.target"
      ],
      "text": "输出包含代码依据的审查建议"
    }
  ],
  "schema_version": 1,
  "scope": [],
  "starting_point": "",
  "status": "ready",
  "target_summary": "用Python实现一个只读的GitHub Code Review Agent，能分析PR并输出有代码依据的审查建议，不自动修改代码。",
  "profile_hash": "caeec606293b5c8d8f7f68da5bfd13f64b3b594093342cb6636d4ec9ba4cc690"
}
```

### Case 3：合成输入与实际结果

规范化Goal输入：

```json
{
  "target": "继续深入学习 Agent 开发，重点提高工具错误处理和任务恢复能力。",
  "scope": [],
  "desired_depth": "unspecified",
  "starting_point": "",
  "outcome_purpose": "learn",
  "constraints": [],
  "project_context": "我已经有一个旅行规划 Agent，希望继续基于它实践。"
}
```

没有模型content/HTTP响应或最终Profile；原样失败：

```json
{
  "error_class": "provider_transport_unknown",
  "message": "Provider outcome unknown",
  "retryable": false,
  "dispatch_unknown": true,
  "details": {
    "requested_model": "deepseek-flash",
    "max_tokens": 4096,
    "thinking": {
      "type": "disabled"
    },
    "purpose": "planning.goal_requirement_analysis",
    "schema": "GoalRequirementProfileV1",
    "finish_reason": null,
    "content_chars": null,
    "reasoning_chars": null,
    "transport_exception_type": "ConnectError"
  },
  "input_tokens": null,
  "output_tokens": null,
  "latency_ms": 5334
}
```

### Case 4：合成输入与实际结果

规范化Goal输入：

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

NOT RUN：Case3 unknown后停止；没有模型输出、Validator结果、Profile或hash，不用Fake补齐。

### Case 5：合成输入与实际结果

规范化Goal输入：

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

NOT RUN：Case3 unknown后停止；没有模型输出、Validator结果、Profile或hash，不用Fake补齐。

### Case 6：合成输入与实际结果

规范化Goal输入：

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

NOT RUN：Case3 unknown后停止；没有模型输出、Validator结果、Profile或hash，不用Fake补齐。

## 4. 独立审查及最小后续建议

独立开发审查请求GPT-6.1 Sol medium，实际解析NOT OBSERVABLE；主协调请求Sol6.1 high、实际解析NOT OBSERVABLE。没有HARD升级，没有让被测Provider自评，也没有创建产品第二Reviewer。独立审查逐案读取合成输入、原始响应及Profile，不以Validator PASS代替语义判断。

独立结论：1 PASS、1 FAIL、4 AMBIGUOUS，完整依据保留于ignored `independent-review.md`。Case2的只读文字没有完全丢失：它在摘要和第三项required中。但上位合同§6规定hard_constraints由I2/5/6适配、I7/8硬约束校验、I9冲突展示消费，`hard_constraints=[]`不履行该独立合同，不能由另一字段保留文字代替。

最小后续建议（未实施）：明确Item1单一Prompt应从target等自然语言提取显式限制，即使structured constraints为空，也要写入hard_constraints并引用goal.target；保留既有结构约束原文保护。不要添加程序NLP黑名单、下游raw-goal二次抽取或第二评审模型。后续修订及新真实验证另需明确授权；不重派Case3 unknown，不覆盖本轮失败证据。

**是否可以进入Item2：否。** 本轮未达到六案通过，且存在真实语义合同缺陷；Item2未启动。

## 5. 回归、保护资产与未运行项目

- 结束边界测试PASS，22项：project_context不能打开public generate；legacy removal/residual保护；transport unknown不泄密、不重试；JSON/truncation失败不retry/repair。全部为既有规则/Mock测试，与上述真实模型响应分开，不冒充真实验收。
- 命令：`.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit backend/tests/unit/test_goal_requirement_input.py::test_project_context_does_not_open_public_generate backend/tests/unit/test_planning_legacy_removal.py backend/tests/unit/test_planning_residual_cleanup.py backend/tests/unit/test_goal_requirement_provider.py::test_transport_unknown_does_not_leak_or_retry backend/tests/unit/test_goal_requirement_provider.py::test_known_response_failures_do_not_retry_or_repair -q --junitxml=var/planning-v2-item1-real-20261008/boundary.xml`，exit0。
- 499份既有backend/frontend/contracts/架构与实现文档/进度/.env文件SHA保持；全部既有账本文件SHA保持。无生产代码、Prompt、Schema、frontend或migration差异。
- `/plans/generate`仍scope后503；未开放公开生成、未恢复旧Planning、未启动Worker/Graph、未触发产品搜索/Reader/WeKnora。
- 新Planning Run0 / Job0 / Draft或Plan mutation0 / DB写入0。调用入口无DB/Repository接线，且既有spy/HTTP fail-closed门禁PASS；这些是入口/依赖访问证据，**不是真实PG行计数**。run_id/attempt_id仅为合成调用账务身份，不代表数据库Run。
- 真实PG/checkpoint验证NOT RUN；Case4～6真实模型NOT RUN；Case3 Profile结构和语义NOT RUN；全backend执行/collection、frontend build、浏览器和完整V2端到端NOT RUN。复用Item1基线已完成离线回归，不声称本轮重复执行。
- 精确费用及Case3实际远端执行结果未知。无新凭据、无额度增加、无push/merge/deploy。全产品保持STAGING_BLOCKED / NOT_READY。

## 6. 修改文件与证据保留

- 唯一新增tracked文件：`docs/planning-v2/ITEM1_REAL_SEMANTIC_SMOKE.md`（本报告）；仅允许本地文档提交，提交SHA在提交后答复，避免自引用。progress和既有Item1报告原文保持。
- ignored目录：`var/planning-v2-item1-real-20261008/`，包含smoke.py/close.py、preflight、每案input/request/raw response/provider/完整Profile、review-packet、independent-review、STOP、boundary日志/XML及final-audit。Case3只有request/失败证据，没有捏造response.body；Case4～6只有packet中的未执行输入。
- ignored恢复检查点：`var/codex-goals/planning-v2-item1-real-semantic-smoke.json`。
- 既有账本仅新增本轮authorization与request/result175～177，历史文件不变；新增unknown177保留，不恢复、不重派。
- 未删任何真实响应或失败日志；本地控制台中文编码失真不代表模型内容损坏，报告与证据统一UTF-8读取。离线汇总首次因Windows默认gbk读取UTF-8失败，已显式UTF-8重做，未产生任何新模型请求。

**ITEM1_SEMANTIC_REVIEW_REQUIRED**

**ITEM2_NOT_STARTED**

**STOP**
