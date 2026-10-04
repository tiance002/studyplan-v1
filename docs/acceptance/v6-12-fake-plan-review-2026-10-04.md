# v6.12 来源明确的新合成计划（Fake / owned PG）

**本轮 BLOCKED，STOP。以下是 Fake 生成并在新 owned PG 合成确认的教学样本，不是 paid provider 生成结果。实际 Plan 的 Edge 消费 NOT RUN。**

Plan `pln_1fdacbddd3f940dcadfce7313a31af6c`；Run `run_b58480c719324f53b94b783a769699f8`；公共来源 agent.application v7；目标：从零系统学习 Agent 应用开发，主要做资料问答，先学通用核心（含 Framework/MCP），再看小型开源核心，然后系统深化 RAG，最后学习成熟 RAG 工程相关切片与迁移验证；不做 RL、Browser、Coding 完整专项。。

实际冻结：18阶段、16个 canonical、18个正式任务；正常请求37、repair上限2、请求上界39、manifest输出上界241664。以上是该 Fake binding 的冻结值；真实 provider binding 免费预检 NOT RUN，未派发收费请求。

outline `stage_skeleton_v1`；structure `reviewed_structure_v1`；focus `stage_focus_v1`；manifest hash `71e2452035be1d010486818d2451df929c861ed5e7da70307ff120d2e54a6f68`。

来源资格来自既有本地受审记录；重绑定不升级正文审核深度。项目候选身份的 metadata_only 与具体教程 selected_sections_read 分别保留；当前源码实际阅读/运行 NOT RUN。

## 本次实际教学顺序

| 顺序 | 阶段 | 单元 / 正式任务 | 教学职责 |

|---|---|---|---|

| 1 | A0 A0 先知道程序在替模型做什么 | 1 / 1 | 公共核心 |

| 2 | A1 A1 最小Agent loop | 1 / 1 | 公共核心 |

| 3 | A2 A2 组件化与受控行动 | 3 / 1 | 公共核心 |

| 4 | A3 A3 简单知识问答 | 1 / 1 | 公共核心 |

| 5 | A4 A4 长会话和上下文预算 | 1 / 1 | 公共核心 |

| 6 | A5 A5 Framework：一个主框架，一次有状态分支与暂停恢复 | 1 / 1 | 公共核心 |

| 7 | A6 A6 MCP：复用只读 server 与最小 server 边界 | 1 / 1 | 公共核心 |

| 8 | A7 A7 系统评价 | 1 / 1 | 公共核心 |

| 9 | A8 A8 小型开源核心学习：Pi 的工具与会话主链 | 1 / 1 | 小型真实源码核心：Pi，whole_core，可替换候选 |

| 10 | G0 专项教程 · 0. 入口：Agent 中的知识检索 | 1 / 1 | 详细 RAG 专项教程 |

| 11 | G1 专项教程 · 1. 入库、解析、切块与来源 | 1 / 1 | 详细 RAG 专项教程 |

| 12 | G2 专项教程 · 2. Embedding、向量库与索引 | 1 / 1 | 详细 RAG 专项教程 |

| 13 | G3 专项教程 · 3. 单路检索 baseline 与评测 | 1 / 1 | 详细 RAG 专项教程 |

| 14 | G4 专项教程 · 4. Hybrid、融合与查询变换 | 1 / 1 | 详细 RAG 专项教程 |

| 15 | G5 专项教程 · 5. Rerank、上下文、回答与 citation | 1 / 1 | 详细 RAG 专项教程 |

| 16 | G6 专项教程 · 6. 集成与回归 | 1 / 1 | 详细 RAG 专项教程 |

| 17 | GR 成熟工程：RAG 入库、检索与引用的选定切片 | 1 / 1 | 成熟 RAG 工程：选定目标切片，案例任选一个 |

| 18 | GT 迁移与验证：RAG 入库、检索与引用 | 1 / 1 | 迁移 / 不迁移理由与改变前后验证 |

## A0 A0 先知道程序在替模型做什么

冻结 stage key：`stage.v62.agent.application.a0`。

能区分模型请求、程序执行与结果消息，用固定响应解释正常和失败路径。

### 实际 LearningUnit

- **A0 先知道程序在替模型做什么**：能区分模型请求、程序执行与结果消息，用固定响应解释正常和失败路径。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a0` — A0 先知道程序在替模型做什么。目标：能区分模型请求、程序执行与结果消息，用固定响应解释正常和失败路径。。前置节点数：0。

### 来源与选中章节

- [Hello-Agents 第1章：初识智能体](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter1)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_cb79ae844606833237ed44e7` — 1.1/1.2 Agent概念。

  - `sec_v612_1eca34edb267f89faaa45ed2` — 1.4 Workflow与Agent。

- [Hello-Agents 第2章：智能体发展史](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter2)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_f8f9ce7b5e45976bd32b1782` — 历史概览（选读）。

- [Hello-Agents 第3章：大语言模型基础](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter3)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_5dd52f1424333906cde4029d` — 3.2.1–3.2.4 应用基础。

  - `sec_v612_1e28991e329155746b25c453` — 3.3.2 生成局限。

- [Python官方中文教程：即时前置](https://docs.python.org/zh-cn/3/tutorial/)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_3bca7f017586a578ec7593e8` — 4.1/4.2/4.8 函数循环。

  - `sec_v612_5b790bf3b17b434305198b2a` — 5.5 字典。

  - `sec_v612_8c337a10e3b7e49727d49482` — 7.2/7.2.2 文件JSON。

  - `sec_v612_eb3ee991aa3938754bd638bb` — 8.2/8.3 异常。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a0",
  "title": "A0 先知道程序在替模型做什么：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n手工给固定模型响应接一个查资料工具，区分模型决定与程序执行",
  "section_key": "stage.v62.agent.application.a0",
  "node_keys": [
    "node.v62.agent.application.a0"
  ],
  "acceptance": [
    "能解释“模型返回命令≠命令已执行”；历史名词不要求全背"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "A0 先知道程序在替模型做什么",
    "previous_relation": "NEW；已会API者REVIEW",
    "learning_focus": [
      "能区分模型请求、程序执行与结果消息，用固定响应解释正常和失败路径。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "项目问题、输入输出、禁止动作清单"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "能解释“模型返回命令≠命令已执行”；历史名词不要求全背"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "review",
    "knowledge_keys": [
      "node.v62.agent.application.a0"
    ],
    "reading_prerequisites": [
      "最小Python诊断"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A1 A1 最小Agent loop

冻结 stage key：`stage.v62.agent.application.a1`。

能实现有停止条件的 Agent loop，追踪工具请求与结果配对，避免无限循环。

### 实际 LearningUnit

- **A1 最小Agent loop**：能实现有停止条件的 Agent loop，追踪工具请求与结果配对，避免无限循环。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a1` — A1 最小Agent loop。目标：能实现有停止条件的 Agent loop，追踪工具请求与结果配对，避免无限循环。。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第4章：智能体经典范式构建](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter4)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_ba4cb406c3d49d926b4f8a8a` — 4.1 LLM与工具入口。

  - `sec_v612_9378017c43551d2ecbc45dfb` — 4.2 ReAct。

- [Learn Claude Code 新版17章](https://github.com/shareAI-lab/learn-claude-code)：comparison；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_f532b7499fc59b38b36aba5b` — s01 Agent Loop。

  - `sec_v612_6a943250d29448d445934a73` — s02 Tool Use。

- [Hello-Agents 第12章：智能体性能评估](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter12)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_429c8806e1dfc1b2d814f28d` — 12.1 评价对象（Eval-Lite预读）。

- [Hello-Agents 第4章：智能体经典范式构建](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter4)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_3fcb472e8494eb8517e1f7cc` — 4.3 Plan-and-Solve。

  - `sec_v612_f79bc2a173a6ca159d6ec1e6` — 4.4 Reflection。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a1",
  "title": "A1 最小Agent loop：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n一个两步资料查询；工具名错、参数错、循环不停三反例",
  "section_key": "stage.v62.agent.application.a1",
  "node_keys": [
    "node.v62.agent.application.a1"
  ],
  "acceptance": [
    "工具选择/参数/最终结果可验证；不用所有范式一起上线"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "A1 最小Agent loop",
    "previous_relation": "NEW + COMPARE",
    "learning_focus": [
      "能实现有停止条件的 Agent loop，追踪工具请求与结果配对，避免无限循环。"
    ],
    "comparison_focus": [
      "ch4 ReAct→Plan-and-Solve→Reflection，保持作者概念到实现链；LCC s01/02只COMPARE"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "可查本地合成资料、记录轨迹与轮数上限"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "工具选择/参数/最终结果可验证；不用所有范式一起上线"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "compare",
    "knowledge_keys": [
      "node.v62.agent.application.a1"
    ],
    "reading_prerequisites": [
      "A0、循环/JSON/异常"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A2 A2 组件化与受控行动

冻结 stage key：`stage.v62.agent.application.a2`。

能定义和派发工具，校验参数与权限，保留未知工具和执行失败的证据。

### 实际 LearningUnit

- **工具契约与注册派发**：解释工具定义、参数校验与按名称派发；比较 Tool 与 registry 职责。关联知识数：1。

- **权限拒绝与职责边界**：解释执行前权限检查与拒绝以后不能继续动作的原因。关联知识数：1。

- **未知工具与执行失败证据**：区分未知工具和执行失败，指出支持结论的记录。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a2` — A2 组件化与受控行动。目标：能定义和派发工具，校验参数与权限，保留未知工具和执行失败的证据。。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第7章：构建你的智能体框架](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter7)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_33afbb915e379439ad0aff94` — 7.1–7.3 Agent与LLM抽象。

  - `sec_v612_263e19094e1b124ecee2e63e` — 7.4–7.5 Tool与registry。

- [Learn Claude Code 新版17章](https://github.com/shareAI-lab/learn-claude-code)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_96b3e1a6d9593f5df3234760` — s03 Permission。

  - `sec_v612_18694cae2117ae63942061b0` — s04 Hooks。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a2",
  "title": "A2 组件化与受控行动：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n用同一工具替换固定响应与API adapter；拒绝写入练习外目录",
  "section_key": "stage.v62.agent.application.a2",
  "node_keys": [
    "node.v62.agent.application.a2"
  ],
  "acceptance": [
    "能解释Tool/registry/LLM各职责；审批拒绝不会仍执行"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "A2 组件化与受控行动",
    "previous_relation": "REVIEW loop；NEW职责分离",
    "learning_focus": [
      "能定义和派发工具，校验参数与权限，保留未知工具和执行失败的证据。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "工具注册、统一错误、超时、审计与行动策略"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "能解释Tool/registry/LLM各职责；审批拒绝不会仍执行"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "review",
    "knowledge_keys": [
      "node.v62.agent.application.a2"
    ],
    "reading_prerequisites": [
      "A1；类不会才补最小接口"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A3 A3 简单知识问答

冻结 stage key：`stage.v62.agent.application.a3`。

能用有限文档检索和对应引用回答问题；证据不足时明确无答案。

### 实际 LearningUnit

- **A3 简单知识问答**：能用有限文档检索和对应引用回答问题；证据不足时明确无答案。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a3` — A3 简单知识问答。目标：能用有限文档检索和对应引用回答问题；证据不足时明确无答案。。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第8章：记忆与检索](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter8)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_94cb8f111a55e50840e9e41b` — 8.1–8.2 Memory。

  - `sec_v612_1b938f530e183b1323d0fe28` — 8.3 RAG。

  - `sec_v612_328e2e362144716866e8983b` — 8.4 文档问答助手。

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_9db9486611ffc5664932ed8e` — ch1 最小RAG四步。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a3",
  "title": "A3 简单知识问答：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n五份合成短文，手工标相关文档；找不到答案时返回不足证据",
  "section_key": "stage.v62.agent.application.a3",
  "node_keys": [
    "node.v62.agent.application.a3"
  ],
  "acceptance": [
    "检索结果可查看；答案带对应证据，能区别Memory和知识库"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "A3 简单知识问答",
    "previous_relation": "REVIEW RAG定义；DEEPEN pipeline",
    "learning_focus": [
      "能用有限文档检索和对应引用回答问题；证据不足时明确无答案。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "资料导入、基础dense检索、来源ID"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "检索结果可查看；答案带对应证据，能区别Memory和知识库"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.a3"
    ],
    "reading_prerequisites": [
      "A2；来源元数据"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A4 A4 长会话和上下文预算

冻结 stage key：`stage.v62.agent.application.a4`。

能区分历史、事实和临时约束，解释召回、裁剪与摘要的上下文预算边界。

### 实际 LearningUnit

- **A4 长会话和上下文预算**：能区分历史、事实和临时约束，解释召回、裁剪与摘要的上下文预算边界。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a4` — A4 长会话和上下文预算。目标：能区分历史、事实和临时约束，解释召回、裁剪与摘要的上下文预算边界。。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第9章：上下文工程](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter9)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_91d618274a302eeee8d12e7c` — 9.1/9.2 上下文原则。

  - `sec_v612_93a99d7cf28e0c3008aa0b3e` — 9.3 ContextBuilder。

- [Learn Claude Code 新版17章](https://github.com/shareAI-lab/learn-claude-code)：comparison；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_ea61bceb7d87cfca60b58c3e` — s08 Context Compact。

  - `sec_v612_0a96a6e3a4759a79967fc48b` — s09 Memory。

- [Hello-Agents 第9章：上下文工程](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter9)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_0265320f8cca542b231b5e41` — 9.4 NoteTool。

  - `sec_v612_8528d367899c1b389aaff192` — 9.5 TerminalTool。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a4",
  "title": "A4 长会话和上下文预算：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n大结果/旧事实/临时限制：哪些召回，哪些裁剪，怎样重读",
  "section_key": "stage.v62.agent.application.a4",
  "node_keys": [
    "node.v62.agent.application.a4"
  ],
  "acceptance": [
    "保存/召回/截断/摘要有独立证据；字符预算不是token精确值"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "A4 长会话和上下文预算",
    "previous_relation": "DEEPEN",
    "learning_focus": [
      "能区分历史、事实和临时约束，解释召回、裁剪与摘要的上下文预算边界。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "研究笔记、选择上下文、引用不可被摘要伪造"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "保存/召回/截断/摘要有独立证据；字符预算不是token精确值"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.a4"
    ],
    "reading_prerequisites": [
      "A3；token与文件"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A5 A5 Framework：一个主框架，一次有状态分支与暂停恢复

冻结 stage key：`stage.v62.agent.application.a5`。

一深多浅：默认沿已审 Hello LangGraph 与 Graph API 组织已有 Tool Agent；其他框架只比较抽象、依赖成本与适用边界。

### 实际 LearningUnit

- **A5 Framework：一个主框架，一次有状态分支与暂停恢复**：一深多浅：默认沿已审 Hello LangGraph 与 Graph API 组织已有 Tool Agent；其他框架只比较抽象、依赖成本与适用边界。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a5` — A5 Framework：一个主框架，一次有状态分支与暂停恢复。目标：能用一个主框架组织有状态、有分支、有明确失败边界的小应用，解释一次最小暂停/恢复。。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第6章：框架开发实践](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter6)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_137eee2c9b24c70ad1247f74` — 6.1 框架位置。

  - `sec_v612_f33f70cc97b9883e11244d05` — 6.3 AgentScope（按目标）。

  - `sec_v612_049052e52e97d7bc6d380c24` — 6.5 LangGraph图基础（按目标）。

- [LangGraph Workflows and Agents guide](https://docs.langchain.com/oss/python/langgraph/workflows-agents)：comparison；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_c0a3feb98540d8a51c6f155e` — Workflows与Agents区别。

- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_d3b04138eef059f97834b17c` — StateGraph/state/nodes/edges/reducers/loop limit。

- [LangGraph Persistence and Checkpointers](https://docs.langchain.com/oss/python/langgraph/persistence)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_eadc441b4ec422862d41ca35` — Checkpoint与Store边界。

- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_cb0cefa603eb83d6ece317b4` — Checkpoint与稳定thread要求。

  - `sec_v612_708dfd60cc8a1d43f39ae7bc` — Command resume/approve/reject/edit。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a5",
  "title": "A5 Framework：一个主框架，一次有状态分支与暂停恢复：沿已有项目验证",
  "goal": "持续实践载体：研究与行动助手\n复用已有工具/状态链，用一个主框架组织分支；注入失败或最小暂停恢复。其他框架只做边界比较，不另造项目。",
  "section_key": "stage.v62.agent.application.a5",
  "node_keys": [
    "node.v62.agent.application.a5"
  ],
  "acceptance": [
    "已有正常/失败链在一个主框架中可解释；一次暂停恢复有证据；比较框架不要求多套实现。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "一深多浅：默认沿已审 Hello LangGraph 与 Graph API 组织已有 Tool Agent；其他框架只比较抽象、依赖成本与适用边界。",
    "previous_relation": "COMPARE：复用已有正常/失败证据，检查不足后补缺；学习安排不代表已验证掌握。",
    "learning_focus": [
      "一深多浅：默认沿已审 Hello LangGraph 与 Graph API 组织已有 Tool Agent；其他框架只比较抽象、依赖成本与适用边界。"
    ],
    "comparison_focus": [
      "当前参考的实现与已学机制有什么相同边界和新增工程问题？"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "一深多浅：默认沿已审 Hello LangGraph 与 Graph API 组织已有 Tool Agent；其他框架只比较抽象、依赖成本与适用边界。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "保存事实/推断分开的正常与失败证据；阅读、clone和运行成功不等于掌握。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "compare",
    "knowledge_keys": [
      "node.v62.agent.application.a5"
    ],
    "reading_prerequisites": [
      "A2 工具、权限与错误证据；不要求先完成完整 RAG。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A6 A6 MCP：复用只读 server 与最小 server 边界

冻结 stage key：`stage.v62.agent.application.a6`。

理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。

### 实际 LearningUnit

- **A6 MCP：复用只读 server 与最小 server 边界**：理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a6` — A6 MCP：复用只读 server 与最小 server 边界。目标：理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第10章：智能体通信协议](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter10)：reference；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_d79f6a54976fb31d5159ac60` — 10.1 协议角色。

- [Hello-Agents 第10章：智能体通信协议](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter10)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_720665da22b1f6c25450e1b4` — 10.2 MCP。

- [Learn Claude Code 新版17章](https://github.com/shareAI-lab/learn-claude-code)：comparison；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_77ad7c40fbafe80bd29db638` — s14 MCP mock工具池。

- [Hello-Agents 第10章：智能体通信协议](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter10)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_6d472bd7c9a9ea48e1e28861` — 10.5 自建server（按目标）。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a6",
  "title": "A6 接外部能力：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n连接受控只读 MCP server，列工具、校验参数与调用；记录未知工具、坏参数、断连；沿 Hello 10.5 阅读或验证最小 server。LCC s14 mock 仅比较，不宣称真实协议互通。",
  "section_key": "stage.v62.agent.application.a6",
  "node_keys": [
    "node.v62.agent.application.a6"
  ],
  "acceptance": [
    "用一次现成受控只读 server 的列工具、参数校验与调用证据解释 host/client/server、transport 和模型 tool calling 的职责；mock 不等于真实 MCP 互通。",
    "沿已审 Hello 10.5 阅读并解释或验证一个最小 server 的工具 schema、分发与结果边界，保留可检查的示例记录。",
    "保存未知工具、坏参数与断连的失败证据，说明权限、敏感信息、输入校验、超时与外部副作用边界。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。",
    "previous_relation": "COMPARE：复用已有正常/失败证据，检查不足后补缺；学习安排不代表已验证掌握。",
    "learning_focus": [
      "理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。"
    ],
    "comparison_focus": [
      "当前参考的实现与已学机制有什么相同边界和新增工程问题？"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "保存事实/推断分开的正常与失败证据；阅读、clone和运行成功不等于掌握。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "compare",
    "knowledge_keys": [
      "node.v62.agent.application.a6"
    ],
    "reading_prerequisites": [
      "A2 工具、输入校验、权限与错误；远程高级认证按目标另选。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A7 A7 系统评价

冻结 stage key：`stage.v62.agent.application.a7`。

A7 系统评价

### 实际 LearningUnit

- **A7 系统评价**：A7 系统评价。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a7` — A7 系统评价。目标：能以正常与失败证据验证：分母与未跑项清楚；judge不是唯一证据；基准成绩不等于产品质量。前置节点数：1。

### 来源与选中章节

- [Hello-Agents 第12章：智能体性能评估](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter12)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_152e231bbed290ad7924cc82` — 12.1 评价入口。

- [LangSmith Evaluation types](https://docs.langchain.com/langsmith/evaluation-types)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_907fdfe84ba1314fc84fc50b` — Unit/Regression/Benchmarking/Pairwise。

- [Hello-Agents 第12章：智能体性能评估](https://github.com/datawhalechina/hello-agents/tree/main/docs/chapter12)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_41e8b9614ae17566a9700fe1` — 12.2 工具调用评价。

  - `sec_v612_30b091409edf26ba2f6ad398` — 12.3 任务成功。

  - `sec_v612_dfd3e9a624d89cb809947ce2` — 12.4 Judge。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a7",
  "title": "A7 系统评价：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n将10条正常/失败任务分开发与held-out，比较基线及一次改动",
  "section_key": "stage.v62.agent.application.a7",
  "node_keys": [
    "node.v62.agent.application.a7"
  ],
  "acceptance": [
    "分母与未跑项清楚；judge不是唯一证据；基准成绩不等于产品质量"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "A7 系统评价",
    "previous_relation": "Lite REVIEW；held-out/专项 DEEPEN",
    "learning_focus": [
      "ch12 12.1→12.2工具调用→12.3任务成功→12.4judge；配合Evaluation专项"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "回归报告、耗时/token、失败分类"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "分母与未跑项清楚；judge不是唯一证据；基准成绩不等于产品质量"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.a7"
    ],
    "reading_prerequisites": [
      "A1起Eval-Lite已贯穿；有任务集和失败轨迹"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## A8 A8 小型开源核心学习：Pi 的工具与会话主链

冻结 stage key：`stage.v62.agent.application.a8`。

whole_core：先看核心地图，再追一条工具请求→执行→结果→下一轮与一条失败链；只读已审 SDK 与 Sessions 文档边界，不全仓遍历。

### 实际 LearningUnit

- **A8 小型开源核心学习：Pi 的工具与会话主链**：whole_core：先看核心地图，再追一条工具请求→执行→结果→下一轮与一条失败链；只读已审 SDK 与 Sessions 文档边界，不全仓遍历。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.a8` — A8 可控真实项目。目标：能解释一个规模可控 Runtime 的工具、状态和失败边界，比较自己的实现并验证一项迁移。。前置节点数：3。

### 来源与选中章节

- [Pi Coding Agent](https://github.com/earendil-works/pi)：case_study；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_2628733002b06848dc68701a` — SDK lifecycle/storage/prompting/events。

  - `sec_v612_9bffef840444e072b2149cf4` — Sessions and Context。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.a8",
  "title": "A8 可控真实项目：小实践与证据",
  "goal": "独立 Micro Exercise：任选一个适合的小型真实核心参考，沿当前源码画工具与状态地图、正常/失败链，对照已有项目并验证一项适用机制；不另建强制毕业 Demo。\n用途：比较/验证本次能力，适合后再迁入用户载体 研究与行动助手；不要求改原项目语言或数据。",
  "section_key": "stage.v62.agent.application.a8",
  "node_keys": [
    "node.v62.agent.application.a8"
  ],
  "acceptance": [
    "有调用地图/边界/迁移验证；不能只展示clone或部署"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "micro_exercise"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "whole_core：先看核心地图，再追一条工具请求→执行→结果→下一轮与一条失败链；只读已审 SDK 与 Sessions 文档边界，不全仓遍历。",
    "previous_relation": "COMPARE：复用已有正常/失败证据，检查不足后补缺；学习安排不代表已验证掌握。",
    "learning_focus": [
      "whole_core：先看核心地图，再追一条工具请求→执行→结果→下一轮与一条失败链；只读已审 SDK 与 Sessions 文档边界，不全仓遍历。"
    ],
    "comparison_focus": [
      "当前参考的实现与已学机制有什么相同边界和新增工程问题？"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "whole_core：先看核心地图，再追一条工具请求→执行→结果→下一轮与一条失败链；只读已审 SDK 与 Sessions 文档边界，不全仓遍历。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "保存事实/推断分开的正常与失败证据；阅读、clone和运行成功不等于掌握。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "compare",
    "knowledge_keys": [
      "node.v62.agent.application.a8"
    ],
    "reading_prerequisites": [
      "A2/A4/A7 正常失败与上下文证据；先确认 SDK 示例中函数/对象、Promise/事件的最小阅读能力，不要求完整 Coding 专项。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": [
    {
      "topic": "项目学习：Pi 轻量 Runtime",
      "concepts": [
        "工具循环",
        "状态边界",
        "失败路径"
      ],
      "guidance": "学习方式：whole_core（有界核心整体认识）\n为什么现在：已有教程基础和最小实践，开始认识真实工程边界。\n重点：工具请求→派发→结果→下一轮，以及会话状态；先画核心地图，再读一条正常和失败链。\n学习深度：只使用已审 SDK lifecycle/storage/prompting/events 与 Sessions and Context 文档范围；项目身份是候选，不声明全仓深审或已经运行。\n暂不涉及：全仓掌握、安装部署、Coding 全专项和安全隔离平台。\n思考问题：谁执行工具？状态保存在哪里？重复或失败如何处理？自己的 Demo 有哪些边界尚不存在？\n预期产物：一张核心调用地图、一个可检查的失败样例、一份事实/推断分开的比较记录。\n迁移候选：最多选择1–2项适合现有实践载体的改进并验证；可选且可替换，匹配的成熟用户项目可承担参考角色。\n外部 Coding Agent 先检查本地已有未提交修改，再打开/定位当前源码；不得覆盖或 reset。用户项目是持续载体，参考候选可替换。",
      "links": [
        "https://github.com/earendil-works/pi"
      ],
      "search_hints": [],
      "thinking_prompts": [
        "自己的 Demo 与参考 Runtime 的边界有哪些差异？"
      ],
      "required": false,
      "order_index": 2
    }
  ]
}
```

## G0 专项教程 · 0. 入口：Agent 中的知识检索

冻结 stage key：`stage.v62.agent.application.g0`。

能区分索引链路与查询链路，比较 A3 已见证据回答与新增检索失败分类。

### 实际 LearningUnit

- **专项教程 · 0. 入口：Agent 中的知识检索**：能区分索引链路与查询链路，比较 A3 已见证据回答与新增检索失败分类。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g0` — 0. 入口：Agent 中的知识检索。目标：能区分索引链路与查询链路，比较 A3 已见证据回答与新增检索失败分类。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_dd71693c7193363a97eb027e` — ch1 RAG导论/最小链路。

- [Hello-Agents：第8章记忆与检索 + 第9章上下文工程（重叠/边界）](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/Chapter8-Memory-and-Retrieval.md)：comparison；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_e8aff3fb666e1454c11ccc88` — 8.3–8.4 Agent中的RAG。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g0",
  "title": "0. 入口：Agent 中的知识检索：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n画写入路径和查询路径，标出 parse、chunk、index、retrieve、context、answer 可能失败点。",
  "section_key": "stage.v62.agent.application.g0",
  "node_keys": [
    "node.v62.agent.application.g0"
  ],
  "acceptance": [
    "能区分离线入库与在线查询，并为每个阶段说出一种可观察失败。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "0. 入口：Agent 中的知识检索；Why now：先把 RAG 放进 Agent 系统边界，再拆解各阶段的失效原因。前置：会读简单 Python 应用；Hello-Agents ch8 已完成则只复习。",
    "previous_relation": "REVIEW/COMPARE：A3 已安排相关概念，不代表已掌握；先确认，再比较本专项新增边界。",
    "learning_focus": [
      "能区分索引链路与查询链路，比较 A3 已见证据回答与新增检索失败分类。"
    ],
    "comparison_focus": [
      "重复的循环/检索机制有哪些？当前软件任务/索引链路新增什么失败边界？"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "画写入路径和查询路径，标出 parse、chunk、index、retrieve、context、answer 可能失败点。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "能区分离线入库与在线查询，并为每个阶段说出一种可观察失败。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "compare",
    "knowledge_keys": [
      "node.v62.agent.application.g0"
    ],
    "reading_prerequisites": [
      "Why now：先把 RAG 放进 Agent 系统边界，再拆解各阶段的失效原因。前置：会读简单 Python 应用；Hello-Agents ch8 已完成则只复习。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## G1 专项教程 · 1. 入库、解析、切块与来源

冻结 stage key：`stage.v62.agent.application.g1`。

1. 入库、解析、切块与来源；Why now：无法追溯来源就不能调试召回、引用或文档更新。前置：阶段0；先用 Markdown/纯文本。OCR、表格解析按真实资料需求 JIT 加入。

### 实际 LearningUnit

- **专项教程 · 1. 入库、解析、切块与来源**：1. 入库、解析、切块与来源；Why now：无法追溯来源就不能调试召回、引用或文档更新。前置：阶段0；先用 Markdown/纯文本。OCR、表格解析按真实资料需求 JIT 加入。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g1` — 1. 入库、解析、切块与来源。目标：能以正常与失败证据验证：每块能定位回原文，失败可见；文档更新/重建时不丢来源关联。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_c4a196a26e74b28f7f17ab3d` — ch2/04 数据加载。

  - `sec_v612_6992cab4f4a2e71bb2597897` — ch2/05 文本切块。

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_9f959062852f2e4f28dbb8d7` — ch8/02 数据准备/父子块。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g1",
  "title": "1. 入库、解析、切块与来源：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n导入虚构 Markdown，显示 chunk preview；保存 source ID、标题、顺序、页/段位置和解析错误；找出并修复一个标题或表格边界问题。",
  "section_key": "stage.v62.agent.application.g1",
  "node_keys": [
    "node.v62.agent.application.g1"
  ],
  "acceptance": [
    "每块能定位回原文，失败可见；文档更新/重建时不丢来源关联。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "1. 入库、解析、切块与来源；Why now：无法追溯来源就不能调试召回、引用或文档更新。前置：阶段0；先用 Markdown/纯文本。OCR、表格解析按真实资料需求 JIT 加入。",
    "previous_relation": "Hello-Agents MarkItDown/chunking REVIEW；解析保真、稳定 provenance、父子块 DEEPEN。第2章 loader 是入门介绍，不代表生产 OCR/表格课程。",
    "learning_focus": [
      "All-in-RAG ch2 04_data_load、05_text_chunking；ch8 02_data_preparation。看 loader 输入输出、固定/递归/Markdown/语义切块与父子块。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "导入虚构 Markdown，显示 chunk preview；保存 source ID、标题、顺序、页/段位置和解析错误；找出并修复一个标题或表格边界问题。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "每块能定位回原文，失败可见；文档更新/重建时不丢来源关联。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.g1"
    ],
    "reading_prerequisites": [
      "Why now：无法追溯来源就不能调试召回、引用或文档更新。前置：阶段0；先用 Markdown/纯文本。OCR、表格解析按真实资料需求 JIT 加入。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## G2 专项教程 · 2. Embedding、向量库与索引

冻结 stage key：`stage.v62.agent.application.g2`。

2. Embedding、向量库与索引；Why now：来源块稳定后再建索引，避免把解析问题误当模型问题。前置：阶段1。向量库部署与模型下载按可用环境/目标 JIT。

### 实际 LearningUnit

- **专项教程 · 2. Embedding、向量库与索引**：2. Embedding、向量库与索引；Why now：来源块稳定后再建索引，避免把解析问题误当模型问题。前置：阶段1。向量库部署与模型下载按可用环境/目标 JIT。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g2` — 2. Embedding、向量库与索引。目标：能以正常与失败证据验证：查询与索引使用匹配的 embedding 版本；可追溯并能按文档 ID 重建索引。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_f88ce1a4c256c553771c7e8f` — ch3/06 文本Embedding。

  - `sec_v612_996cbe88d6768714f70b73c3` — ch3/08 向量数据库。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g2",
  "title": "2. Embedding、向量库与索引：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n为每个 chunk 保存稳定 ID、模型名/版本、向量维度与 metadata；检查向量可回到原文。",
  "section_key": "stage.v62.agent.application.g2",
  "node_keys": [
    "node.v62.agent.application.g2"
  ],
  "acceptance": [
    "查询与索引使用匹配的 embedding 版本；可追溯并能按文档 ID 重建索引。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "2. Embedding、向量库与索引；Why now：来源块稳定后再建索引，避免把解析问题误当模型问题。前置：阶段1。向量库部署与模型下载按可用环境/目标 JIT。",
    "previous_relation": "Hello-Agents Embedding/Qdrant REVIEW；增加 chunk ID、metadata、模型/维度版本契约 DEEPEN。多模态和分布式 Milvus 不是普遍前置。",
    "learning_focus": [
      "All-in-RAG ch3 06_vector_embedding、08_vector_db；按资料形态选读 07_multimodal_embedding、09_milvus、10_index_optimization。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "为每个 chunk 保存稳定 ID、模型名/版本、向量维度与 metadata；检查向量可回到原文。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "查询与索引使用匹配的 embedding 版本；可追溯并能按文档 ID 重建索引。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.g2"
    ],
    "reading_prerequisites": [
      "Why now：来源块稳定后再建索引，避免把解析问题误当模型问题。前置：阶段1。向量库部署与模型下载按可用环境/目标 JIT。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## G3 专项教程 · 3. 单路检索 baseline 与评测

冻结 stage key：`stage.v62.agent.application.g3`。

3. 单路检索 baseline 与评测；Why now：先有可重复的基线，才能判断后续加方法是否真在解决问题。前置：阶段1–2；建立小型人工核验 query/相关 chunk 集。

### 实际 LearningUnit

- **专项教程 · 3. 单路检索 baseline 与评测**：3. 单路检索 baseline 与评测；Why now：先有可重复的基线，才能判断后续加方法是否真在解决问题。前置：阶段1–2；建立小型人工核验 query/相关 chunk 集。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g3` — 3. 单路检索 baseline 与评测。目标：能以正常与失败证据验证：能复现 baseline；分清解析缺失、未召回、排序差和答案错误。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_b2f7a3181f93f101933fc204` — ch4/11 检索基础。

- [Ragas 官方文档：Quick Start、RAG metrics 与评估工作流](https://docs.ragas.io/en/stable/getstarted/quickstart/)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_f1f08e044a60f3522dc72f0d` — Context Precision/Recall定义与口径。

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_6d0cf93f72a097ace870cd17` — ch6/18 系统评估。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g3",
  "title": "3. 单路检索 baseline 与评测：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n先独立运行 lexical/BM25 与 dense（缺模型时可用固定 stub 先校验接口）；按精确术语、语义改写、跨段、不可回答分组记录坏例。",
  "section_key": "stage.v62.agent.application.g3",
  "node_keys": [
    "node.v62.agent.application.g3"
  ],
  "acceptance": [
    "能复现 baseline；分清解析缺失、未召回、排序差和答案错误。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "3. 单路检索 baseline 与评测；Why now：先有可重复的基线，才能判断后续加方法是否真在解决问题。前置：阶段1–2；建立小型人工核验 query/相关 chunk 集。",
    "previous_relation": "Hello-Agents 没有系统检索/回答闭环，属 NEW。Ragas ContextPrecision/ContextRecall 与传统 IR 指标同名相近但计算口径不同。",
    "learning_focus": [
      "All-in-RAG ch4 11_hybrid_search 中的检索基础、ch6 18_system_evaluation：BM25/dense、Precision/Recall/MRR/MAP 与评估工具概念。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "先独立运行 lexical/BM25 与 dense（缺模型时可用固定 stub 先校验接口）；按精确术语、语义改写、跨段、不可回答分组记录坏例。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "能复现 baseline；分清解析缺失、未召回、排序差和答案错误。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "unknown",
    "knowledge_keys": [
      "node.v62.agent.application.g3"
    ],
    "reading_prerequisites": [
      "Why now：先有可重复的基线，才能判断后续加方法是否真在解决问题。前置：阶段1–2；建立小型人工核验 query/相关 chunk 集。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## G4 专项教程 · 4. Hybrid、融合与查询变换

冻结 stage key：`stage.v62.agent.application.g4`。

4. Hybrid、融合与查询变换；Why now：只有 baseline 显示某类 query 召回不足时，才选择增加检索通道或改写。前置：阶段3，有固定测试集和通道级结果。

### 实际 LearningUnit

- **专项教程 · 4. Hybrid、融合与查询变换**：4. Hybrid、融合与查询变换；Why now：只有 baseline 显示某类 query 召回不足时，才选择增加检索通道或改写。前置：阶段3，有固定测试集和通道级结果。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g4` — 4. Hybrid、融合与查询变换。目标：能以正常与失败证据验证：能准确解释通道和融合差异；不把论文/示例平均值推广成所有语料均有效。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_0da7f6d1dc871b2f1583f7c6` — ch4/11 Hybrid。

  - `sec_v612_b9560bee9613fd6f007c63a4` — ch4/12 查询构造。

  - `sec_v612_bb587a899d96b2947fef82cd` — ch4/14 查询改写。

- [BGE-M3 官方模型卡与论文：dense / learned sparse / multi-vector](https://huggingface.co/BAAI/bge-m3)：comparison；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_35b1d1583e9e3b96932be058` — Dense/Learned sparse与独立BM25基线。

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_443d13cab56a49c00fe744cf` — ch8/03 BM25+dense+RRF。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g4",
  "title": "4. Hybrid、融合与查询变换：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n保留各通道候选与最终顺序；同一测试集每轮只改一个因素，观察哪些 query 类型改善、哪些回退。",
  "section_key": "stage.v62.agent.application.g4",
  "node_keys": [
    "node.v62.agent.application.g4"
  ],
  "acceptance": [
    "能准确解释通道和融合差异；不把论文/示例平均值推广成所有语料均有效。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "4. Hybrid、融合与查询变换；Why now：只有 baseline 显示某类 query 召回不足时，才选择增加检索通道或改写。前置：阶段3，有固定测试集和通道级结果。",
    "previous_relation": "Hello-Agents MQE/HyDE REVIEW + COMPARE；显式 BM25+dense、RRF、通道诊断 NEW/DEEPEN。Text2SQL/Cypher 仅按数据需求选读。",
    "learning_focus": [
      "All-in-RAG ch4 11_hybrid_search、12_query_construction、14_query_rewriting；ch8 03_index_retrieval。对比 BM25、dense、BGE-M3 learned sparse、RRF、weighted fusion、metadata filter、MQE、HyDE、step-back、rewrite、routing。"
    ],
    "comparison_focus": [
      "Hello-Agents MQE/HyDE REVIEW + COMPARE；显式 BM25+dense、RRF、通道诊断 NEW/DEEPEN。Text2SQL/Cypher 仅按数据需求选读。"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "保留各通道候选与最终顺序；同一测试集每轮只改一个因素，观察哪些 query 类型改善、哪些回退。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "能准确解释通道和融合差异；不把论文/示例平均值推广成所有语料均有效。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "compare",
    "knowledge_keys": [
      "node.v62.agent.application.g4"
    ],
    "reading_prerequisites": [
      "Why now：只有 baseline 显示某类 query 召回不足时，才选择增加检索通道或改写。前置：阶段3，有固定测试集和通道级结果。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## G5 专项教程 · 5. Rerank、上下文、回答与 citation

冻结 stage key：`stage.v62.agent.application.g5`。

5. Rerank、上下文、回答与 citation；Why now：候选已含正确证据但排序或答案组装失败时，才加 rerank 和 context 策略。前置：阶段3–4；回答层只接本轮真实检索证据。

### 实际 LearningUnit

- **专项教程 · 5. Rerank、上下文、回答与 citation**：5. Rerank、上下文、回答与 citation；Why now：候选已含正确证据但排序或答案组装失败时，才加 rerank 和 context 策略。前置：阶段3–4；回答层只接本轮真实检索证据。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g5` — 5. Rerank、上下文、回答与 citation。目标：能以正常与失败证据验证：每条实质性 claim 能回到原文；引用不存在、错位、不支持 claim 和资料不足却作答都能被测试识别。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_61e30ddba4f5feb7e4a59f1c` — ch4/15 高级检索/Rerank。

  - `sec_v612_5265a84a9a1abf4e86612403` — ch5/16 格式化生成。

- [RAG source citations：Microsoft RAG 指南与 Cohere structured citations](https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_b0b183f1f8fbda894c084d95` — 来源元数据与claim支持性。

  - `sec_v612_e0ac8266f12fdb7907985c3f` — Cohere结构化citation对象。

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_361a8176cf0bdbf33f72a43d` — ch8/04 回答集成。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g5",
  "title": "5. Rerank、上下文、回答与 citation：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n尝试候选 rerank、父块展开、压缩/去重和长度控制；答案带 chunk ID 与文件位置；加无证据问题及错误引用样例。",
  "section_key": "stage.v62.agent.application.g5",
  "node_keys": [
    "node.v62.agent.application.g5"
  ],
  "acceptance": [
    "每条实质性 claim 能回到原文；引用不存在、错位、不支持 claim 和资料不足却作答都能被测试识别。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "5. Rerank、上下文、回答与 citation；Why now：候选已含正确证据但排序或答案组装失败时，才加 rerank 和 context 策略。前置：阶段3–4；回答层只接本轮真实检索证据。",
    "previous_relation": "父子上下文、去重、证据绑定 DEEPEN；结构化 source citation 与 correctness NEW。citation prompt 规定格式，不证明 claim 被证据支持。",
    "learning_focus": [
      "All-in-RAG ch4 15_advanced_retrieval_techniques、ch5 16_formatted_generation、ch8 04_generation_sys；补 Microsoft RAG/index provenance、Cohere RAG citations、RAGFlow citation prompt 或 WeKnora references API。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "尝试候选 rerank、父块展开、压缩/去重和长度控制；答案带 chunk ID 与文件位置；加无证据问题及错误引用样例。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "每条实质性 claim 能回到原文；引用不存在、错位、不支持 claim 和资料不足却作答都能被测试识别。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.g5"
    ],
    "reading_prerequisites": [
      "Why now：候选已含正确证据但排序或答案组装失败时，才加 rerank 和 context 策略。前置：阶段3–4；回答层只接本轮真实检索证据。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## G6 专项教程 · 6. 集成与回归

冻结 stage key：`stage.v62.agent.application.g6`。

6. 集成与回归；Why now：各组件可以单独诊断后，才把 pipeline 串起来并判断改动是否改善端到端结果。前置：阶段1–5通过。

### 实际 LearningUnit

- **专项教程 · 6. 集成与回归**：6. 集成与回归；Why now：各组件可以单独诊断后，才把 pipeline 串起来并判断改动是否改善端到端结果。前置：阶段1–5通过。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g6` — 6. 集成与回归。目标：能以正常与失败证据验证：每个坏例能定位到阶段；变更可复测；答案支持性、引用、拒答和检索指标均有记录。。前置节点数：1。

### 来源与选中章节

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：primary；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_0ef1e6483adf3e31c8ddce22` — ch6/19 评估工具（按需）。

- [All-in-RAG：大模型应用开发实战一：RAG 技术全栈指南](https://github.com/datawhalechina/all-in-rag)：supplement；证据深度 `selected_sections_read`；实际运行 `not_run`。

  - `sec_v612_a31306ebb48dd582c56264b8` — ch8/01 环境与架构。

  - `sec_v612_c6746440f570a8070cda4e9c` — ch8/02 数据准备。

  - `sec_v612_582cd4799f6eee3583681909` — ch8/03 索引检索。

  - `sec_v612_98500c15463697d3e243ac20` — ch8/04 生成集成。

### 本地权威任务

```json
{
  "stable_key": "practice.v62.agent.application.g6",
  "title": "6. 集成与回归：小实践与证据",
  "goal": "持续实践载体：研究与行动助手\n将导入、chunk、index、BM25/dense、融合、context、回答、引用接通；对同一问题集回归，不可回答样本要拒答。",
  "section_key": "stage.v62.agent.application.g6",
  "node_keys": [
    "node.v62.agent.application.g6"
  ],
  "acceptance": [
    "每个坏例能定位到阶段；变更可复测；答案支持性、引用、拒答和检索指标均有记录。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "6. 集成与回归；Why now：各组件可以单独诊断后，才把 pipeline 串起来并判断改动是否改善端到端结果。前置：阶段1–5通过。",
    "previous_relation": "Hello-Agents PDF 助手 REVIEW；本阶段增加版本化测试数据、索引和配置快照、badcase 修复后回归。",
    "learning_focus": [
      "All-in-RAG ch8 01_env_architecture 至 04_generation_sys；ch6 19_common_tools 按需。"
    ],
    "comparison_focus": [],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "将导入、chunk、index、BM25/dense、融合、context、回答、引用接通；对同一问题集回归，不可回答样本要拒答。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "每个坏例能定位到阶段；变更可复测；答案支持性、引用、拒答和检索指标均有记录。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "review",
    "knowledge_keys": [
      "node.v62.agent.application.g6"
    ],
    "reading_prerequisites": [
      "Why now：各组件可以单独诊断后，才把 pipeline 串起来并判断改动是否改善端到端结果。前置：阶段1–5通过。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## GR 成熟工程：RAG 入库、检索与引用的选定切片

冻结 stage key：`stage.v612.agent.application.gr`。

DEEPEN：任选一个受控候选，选定一个 RAG 入库、检索与引用 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。

### 实际 LearningUnit

- **成熟工程：RAG 入库、检索与引用的选定切片**：DEEPEN：任选一个受控候选，选定一个 RAG 入库、检索与引用 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g6` — 6. 集成与回归。目标：能以正常与失败证据验证：每个坏例能定位到阶段；变更可复测；答案支持性、引用、拒答和检索指标均有记录。。前置节点数：1。

### 来源与选中章节

- [Agent：RAGFlow](https://github.com/infiniflow/ragflow)：case_study；证据深度 `metadata_only`；实际运行 `not_run`。

- [Agent：WeKnora](https://github.com/Tencent/WeKnora)：case_study；证据深度 `metadata_only`；实际运行 `not_run`。

### 本地权威任务

```json
{
  "stable_key": "practice.v612.agent.application.gr",
  "title": "成熟工程：RAG 入库、检索与引用的选定切片：一个可替换能力任务",
  "goal": "持续实践载体：研究与行动助手\nDEEPEN：任选一个受控候选，选定一个 RAG 入库、检索与引用 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。",
  "section_key": "stage.v612.agent.application.gr",
  "node_keys": [
    "node.v62.agent.application.g6"
  ],
  "acceptance": [
    "任选一个可替换案例证明同一能力；保存当前实现地图、一条失败链、与已学机制的比较及验证证据。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "DEEPEN：任选一个受控候选，选定一个 RAG 入库、检索与引用 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。",
    "previous_relation": "DEEPEN：复用已有正常/失败证据，检查不足后补缺；学习安排不代表已验证掌握。",
    "learning_focus": [
      "DEEPEN：任选一个受控候选，选定一个 RAG 入库、检索与引用 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。"
    ],
    "comparison_focus": [
      "当前参考的实现与已学机制有什么相同边界和新增工程问题？"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "DEEPEN：任选一个受控候选，选定一个 RAG 入库、检索与引用 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "保存事实/推断分开的正常与失败证据；阅读、clone和运行成功不等于掌握。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.g6"
    ],
    "reading_prerequisites": [
      "专项教程 · 6. 集成与回归 已有证据；whole_core 学习只提供入场，不代表专项通关。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": [
    {
      "topic": "项目学习：Agent：RAGFlow",
      "concepts": [
        "上传到解析；异步入库；召回与融合；引用定位；评估与失败可见性。"
      ],
      "guidance": "学习方式：targeted_deep_dive（目标相关切片）\n为什么现在：基础RAG能诊断问题，需要观察文档解析、任务入库与引用证据如何集成。\n重点：上传到解析；异步入库；召回与融合；引用定位；评估与失败可见性。\n必要前置：All-in-RAG核心流水线；明确检索与答案评估；Docker最小运行知识。\n学习深度：单个文档/单个问题端到端，沿当前代码动态定位。\n暂不涉及：所有解析器、全UI、所有部署平台、多租户内部机制一次学完。\n思考问题：解析产物保存什么？页码与chunk如何绑定？某一步失败是否能重试？原文删除后引用怎么办？低召回与生成错误怎样区分？\n预期产物：入库与查询两张地图、一例失败归因、引用来源表。\n迁移候选：页码/来源的稳定证据链；分阶段bad-case日志。\n可选且可替换；用户项目优先。小项目先地图，大项目3–8个动态切片，一次一个；事实/解释/推断分开，最多迁移1–2项；使用当前源码，不固定commit/branch/path/function。\n参考学习项目与持续实践载体分开；初学 Demo 不代表成熟工程认识。\n本阶段只任选一个可替换案例完成同一能力任务，不要求每个仓库各做一次。外部AI检查本地未提交修改后定位当前源码；记录实际阅读版本，不锁公共commit/path/function。",
      "links": [
        "https://github.com/infiniflow/ragflow"
      ],
      "search_hints": [],
      "thinking_prompts": [
        "解析产物保存什么？页码与chunk如何绑定？某一步失败是否能重试？原文删除后引用怎么办？低召回与生成错误怎样区分？"
      ],
      "required": false,
      "order_index": 0,
      "project_study_card": {
        "repo_url": "https://github.com/infiniflow/ragflow",
        "why_now": "基础RAG能诊断问题，需要观察文档解析、任务入库与引用证据如何集成。",
        "prerequisites": "All-in-RAG核心流水线；明确检索与答案评估；Docker最小运行知识。",
        "known_knowledge": "chunk/embedding/dense/sparse/fusion/rerank/context。",
        "study_mode": "大型成熟项目，5切片；本卡是研究目标，不是已读全源码的结论。",
        "learning_focus": "上传到解析；异步入库；召回与融合；引用定位；评估与失败可见性。",
        "desired_depth": "单个文档/单个问题端到端，沿当前代码动态定位。",
        "important_questions": "解析产物保存什么？页码与chunk如何绑定？某一步失败是否能重试？原文删除后引用怎么办？低召回与生成错误怎样区分？",
        "avoid_scope": "所有解析器、全UI、所有部署平台、多租户内部机制一次学完。",
        "expected_outputs": "入库与查询两张地图、一例失败归因、引用来源表。",
        "migration_candidates": "页码/来源的稳定证据链；分阶段bad-case日志。",
        "title": "Agent：RAGFlow",
        "binding": "optional",
        "replacement_allowed": true,
        "status": "reviewed_candidate"
      }
    },
    {
      "topic": "项目学习：Agent：WeKnora",
      "concepts": [
        "知识导入生命周期；检索与对话；会话/知识权限；结果证据与运行诊断。"
      ],
      "guidance": "学习方式：targeted_deep_dive（目标相关切片）\n为什么现在：想学习知识库应用的服务边界与检索能力组合；与RAGFlow等候选按目标选择；用户指定项目优先，不限定候选数量或来源。\n重点：知识导入生命周期；检索与对话；会话/知识权限；结果证据与运行诊断。\n必要前置：RAG核心练习与查询评估完成；懂API/DB配置。\n学习深度：理解模块契约与一条当前调用链，不要求掌握所有语言与基础设施。\n暂不涉及：未经源码核查就声称已有某项实现；全部UI/所有集成。\n思考问题：检索条件和用户身份从哪里传递？前一轮历史会否污染知识检索？入库部分失败如何标识？证据与回答怎样关联？\n预期产物：API到数据流地图、权限边界、失败样例。\n迁移候选：会话隔离、知识生命周期状态。\n可选且可替换；用户项目优先。小项目先地图，大项目3–8个动态切片，一次一个；事实/解释/推断分开，最多迁移1–2项；使用当前源码，不固定commit/branch/path/function。\n参考学习项目与持续实践载体分开；初学 Demo 不代表成熟工程认识。\n本阶段只任选一个可替换案例完成同一能力任务，不要求每个仓库各做一次。外部AI检查本地未提交修改后定位当前源码；记录实际阅读版本，不锁公共commit/path/function。",
      "links": [
        "https://github.com/Tencent/WeKnora"
      ],
      "search_hints": [],
      "thinking_prompts": [
        "检索条件和用户身份从哪里传递？前一轮历史会否污染知识检索？入库部分失败如何标识？证据与回答怎样关联？"
      ],
      "required": false,
      "order_index": 1,
      "project_study_card": {
        "repo_url": "https://github.com/Tencent/WeKnora",
        "why_now": "想学习知识库应用的服务边界与检索能力组合；与RAGFlow等候选按目标选择；用户指定项目优先，不限定候选数量或来源。",
        "prerequisites": "RAG核心练习与查询评估完成；懂API/DB配置。",
        "known_knowledge": "同RAGFlow卡，不重新从RAG定义学起。",
        "study_mode": "4切片。",
        "learning_focus": "知识导入生命周期；检索与对话；会话/知识权限；结果证据与运行诊断。",
        "desired_depth": "理解模块契约与一条当前调用链，不要求掌握所有语言与基础设施。",
        "important_questions": "检索条件和用户身份从哪里传递？前一轮历史会否污染知识检索？入库部分失败如何标识？证据与回答怎样关联？",
        "avoid_scope": "未经源码核查就声称已有某项实现；全部UI/所有集成。",
        "expected_outputs": "API到数据流地图、权限边界、失败样例。",
        "migration_candidates": "会话隔离、知识生命周期状态。",
        "title": "Agent：WeKnora",
        "binding": "optional",
        "replacement_allowed": true,
        "status": "reviewed_candidate"
      }
    }
  ]
}
```

## GT 迁移与验证：RAG 入库、检索与引用

冻结 stage key：`stage.v612.agent.application.gt`。

从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。

### 实际 LearningUnit

- **迁移与验证：RAG 入库、检索与引用**：从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。。关联知识数：1。

### 受控知识与前置

- `node.v62.agent.application.g6` — 6. 集成与回归。目标：能以正常与失败证据验证：每个坏例能定位到阶段；变更可复测；答案支持性、引用、拒答和检索指标均有记录。。前置节点数：1。

### 来源与选中章节

### 本地权威任务

```json
{
  "stable_key": "practice.v612.agent.application.gt",
  "title": "迁移与验证：RAG 入库、检索与引用：一个可替换能力任务",
  "goal": "持续实践载体：研究与行动助手\n从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。",
  "section_key": "stage.v612.agent.application.gt",
  "node_keys": [
    "node.v62.agent.application.g6"
  ],
  "acceptance": [
    "选择1–2项适合持续项目的机制，保存最小改动或明确不迁移理由；不因参考项目存在而强制替换用户项目。",
    "复用已有固定坏例，对照改变前后的正常/失败与回归证据，说明改善、退化和适用边界。"
  ],
  "design_status": "not_run",
  "carrier_policy": "user_project_first_or_micro_exercise",
  "adaptation_mode": "carrier"
}
```

### 教学指导与参考项目边界

```json
{
  "guidance": {
    "why_now": "从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。",
    "previous_relation": "DEEPEN：复用已有正常/失败证据，检查不足后补缺；学习安排不代表已验证掌握。",
    "learning_focus": [
      "从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。"
    ],
    "comparison_focus": [
      "当前参考的实现与已学机制有什么相同边界和新增工程问题？"
    ],
    "practice_delta": {
      "baseline": "默认项目候选（可替换）：研究与行动助手。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。",
      "increment": [
        "从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。"
      ],
      "preserved": [
        "保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。"
      ],
      "validation": [
        "保存事实/推断分开的正常与失败证据；阅读、clone和运行成功不等于掌握。"
      ],
      "reuse": [
        "按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。"
      ]
    },
    "source_slice": null,
    "exposure_relation": "deepen",
    "knowledge_keys": [
      "node.v62.agent.application.g6"
    ],
    "reading_prerequisites": [
      "专项教程 · 6. 集成与回归 已有证据；whole_core 学习只提供入场，不代表专项通关。"
    ],
    "practice_prerequisites": [
      "优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。",
      "先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。"
    ]
  },
  "project_cards": []
}
```

## 其他新样本

窄 MCP：A0→A1→A2→A6；Agent专项待选：A0–A8。Node API部署：S0→S1→S2→SC小服务核心→S3→S7→S8官方可观测教程→SR成熟Telemetry切片→S9→S10→S13。均为新Fake/owned PG样本。

Browser/框架已知起点在本轮定向UNIT与离线选择验证；完整持久化 Browser 代表 NOT RUN。Coding 无独立已审 TypeScript 语言课程：Pi SDK Promise/event 只作有边界的阅读检查，不足时 needs_research_or_review。

未开放体验服务器，没有可用浏览器访问地址。账号与 owned DSN 仅保存在受保护的本机 private 证据目录，不进入本报告。
