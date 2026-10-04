# 代码事实与本轮改动定位

## 1. 审查版本与证据等级

2026-10-04，GitHub `feat/n1-resource-discovery` 返回 `ff3b6c42c16b0ec2b634b45441251cb8dc1e3249`。这是 v6.8 版本。用户报告 v6.10 本地提交 `817b17b`、`1a3262e` 未推送；本次未获得两者完整源码，也未获得 A2 三份原始 provider 正文。

本次证据分三类：

- **SOURCE**：实际读取该远端 SHA 的源码，下面给出具体符号和路径。
- **REPORT**：用户上传的 v6.10 验收报告与 `progress(5).md`。其测试 PASS/FAIL 是实施方报告，不是本次重跑。
- **PROPOSAL / TO_VERIFY**：本次设计建议、需要 Codex 在最新本机源码确认的部分。

没有将旧源码缺陷直接认定为 v6.10 仍未修复；没有声称本次执行测试或复核原始付费响应。

## 2. 最重要的代码发现：单元层已经存在

**SOURCE：`backend/app/domain/catalog/models.py`**

已有 `KnowledgeNode`、`LearningUnit`、`UnitNodeLink`。`LearningUnit` 具备 title、objectives、rubric、rubric_version；`UnitNodeLink` 明确一个单元多节点、一个节点可由多单元复用。KnowledgeNode 有 source_status，默认 ai_draft。

**含义**：不需要新建 Capability→Concept→Topic→Unit 四层数据库来解决 A2。当前问题是生成合同和数据使用方式，不是实体缺失。此前“一阶段一节点”的表述只适用于受控 Pack 的粗粒度内容映射，不是数据库根本不支持细分。

源码：
https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/domain/catalog/models.py

## 3. 模型输出职责仍然过宽，局部校验却要求固定目录

**SOURCE：`backend/app/infrastructure/providers/openai_compatible.py`**

`SHAPES['planning.structure']` 仍示范 nodes、units、relations，并包含示例 `node.topic.child`。通用 system 要求模型生成当前阶段的知识节点、关系与教学单元；要求 preserve supplied keys，但没有将“受控目录模式”收窄为只编排单元。新短 outline 使用独立 OUTLINE_SYSTEM/SHAPE，structure 尚未走等价分支。

**SOURCE：`backend/app/agent_workflows/planning_batches.py`**

`validate_structure_batch()` 要求完整 nodes/units/relations。对存在明确节点清单的受控阶段，`node_keys - declared_owned` 不为空会报“新增未审核知识节点”。它允许多个 units 关联相同节点，不要求一阶段只有一个 unit。

**SOURCE：`backend/app/agent_workflows/nodes.py`**

`generate_structure_batch()` → `KnowledgeStructureV1` → `validate_structure_batch_node()` → `repair_batch()`。repair 是整条 Run 共享最多两次，不是每阶段两次。

**REPORT**：v6.10 A2 增加六个未声明 key；repair1 缺完整字段，repair2 仍有额外 key。HTTP200/stop、不存在本轮 unknown。因此不是本轮 DNS／输出截断故障。

**TO_VERIFY**：六个子主题是否处在 A2 受审范围内，必须读原始正文；目前不能说六项都合理，也不能仅凭 key 未声明判它们的教学概念都错误。检查实际 repair 请求是否已包含正确完整 shape、allowed keys、具体 field-path errors。不能把推断写成根因已全部确认。

源码：
https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/infrastructure/providers/openai_compatible.py
https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/agent_workflows/planning_batches.py
https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/agent_workflows/nodes.py

## 4. 输入投影与回填：哪里能做薄适配

**SOURCE**：`structure_payload()` 只取当前 stage 的 node_blueprints、required_unit_node_keys、resources refs、learning_guidance 和已声明外部前置，没有搬回完整大包。但投影没有完整传递知识 scope/acceptance。

**SOURCE**：当前 reviewed merge 会从本地 authority 恢复知识正文和正式依赖；practice 同样回填任务，并把 canonical_knowledge / canonical_practice 写进已有 unit.rubric。这个实现会整体赋值 rubric。

**建议**：在生成边界新增未来 Run 的“单元组织模式”，模型只产 units；本地重建 canonical nodes/relations，形成原下游 shape，再走现有完整验证、practice 和 publisher。若 teaching notes 需要放 rubric，必须允许一个受限呈现命名空间，再由服务端写入 canonical 命名空间；不能用 merge 覆盖掉刚生成的单元教学细节，也不能允许模型覆盖 canonical_*。

输入必须包含足够的受控能力范围／允许教学重点以避免“只有 key”的盲编排；但仍限当前阶段，不重带资源审核全文与发布材料。

## 5. Framework/MCP 与项目阶段：资料已有，选择和角色需调整

**SOURCE：`backend/app/tools/map_semantic_content.py` 的 BINDINGS**

- A5 已绑定 Hello ch6 框架相关范围、LangGraph workflows 对照。
- A6 已绑定 Hello ch10 MCP／自建 server，以及 LCC s14 mock 对照。
- 远端旧 A8 无资源绑定，项目卡集中在 C10、G6、W5、W7、B7 等。
- G0–G7、C1–C10、W0–W7、B0–B7 已有按章教学范围，不需要再从零研究一套课程。

**REPORT**：v6.10 已修 A8 Pi 绑定、完整／窄范围、排除、载体适配、多候选与长文本消费。必须复用这些修复。新要求不是再做一次“补A8”，而是：

1. 完整 Agent 默认包含 A5/A6 的真实教学内容；窄目标不机械全套。
2. 原 A8 的后继单元只承担小型源码整体核心学习。
3. 所选专项教程保持多个阶段。
4. 成熟项目切片形成独立学习阶段，不和教程尾章混在同一大阶段里。

源码：
https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/backend/app/tools/map_semantic_content.py

## 6. 后端生成多个单元还不够，页面要真正展示

**SOURCE：`frontend/src/features/learning/MainWorkspace.tsx`**

远端版本主要呈现阶段、KnowledgeNode、resources、guidance、extensions。`stage.units` 主要用于资料偏好／补充资料对话框的选择，未见普通学习主区的逐单元教学序列。

**REPORT**：v6.10 说项目卡多候选和续片已修；没有声明本次新增了完整的 LearningUnit 学习序列。

**TO_VERIFY**：核对本机最新 Unit DTO 与 WorkspaceView。若多单元已展示，复用并补用例；否则在现有主区增加按 order_index 的简洁单元列表，显示标题、学习目标和已链接知识。不能只在开发 JSON 中存在几个 units 就记为“允许拆课已完成”。

源码：
https://github.com/tiance002/studyplan-v1/blob/ff3b6c42c16b0ec2b634b45441251cb8dc1e3249/frontend/src/features/learning/MainWorkspace.tsx

## 7. 预算与全路线可见性

**SOURCE：`freeze_manifest()`**

当前一个 outline、每阶段一个 structure 和一个 practice，加整 Run 最多两次 repair。请求上界 `1 + structure_batches + practice_batches + 2`，预算随实际阶段数冻结。

**含义**：把 A8 拆开不能继续写死“7阶段/17次”。也不能为了省调用删 Framework、MCP、专项或大项目，再说完整覆盖。教学分段与模型派发单位应分开理解：同一阶段多 LearningUnit 不额外引入模型调用。

本轮先沿用分批执行器，不顺手重做惰性规划／分段新任务平台。完整可见路线不要求给所有候选专项生成全部正文，但明确选中的专项必须展开其教学与工程阶段。

## 8. 优先级和非目标

| 优先级 | 改动 | 主要复用点 |
|---|---|---|
| P0 | 受控 structure 只组织教学单元；repair合同一致 | provider、nodes、batch validator、existing merge |
| P0 | A5/A6 公共完整主线 + 源码整体／专项／成熟切片分段 | v6.10 selector、next Pack 构建器 |
| P0 | 多单元普通页面可见，完整路线不再隐藏后段 | Workspace、existing UnitView、ProjectStudyCard |
| P1 | 公开冻结范围、证据等级、所选／待选路线给用户审阅 | 受控导出、guidance、现有扩展 |
| 不做 | 全量概念图谱重构、全局相似度去重、AST/Repo RAG、新队列、多 Agent 调度器 | 本轮不需要 |

## 9. 本轮未证实、不能扩大结论的事项

- 未直接读到 Agent6 的最终 JSON，也没有 v6.10 failed raw responses；N0 必须取得。
- 未亲自验证 v6.10 所报告测试结果。
- `reviewed` 不等于用户逐条人工审核，不等于内容永远正确或教程已经运行。
- 小型/大型分类是学习范围，不是当前仓库大小、star 或成熟度的外部评测。
- 新包与新 contract 能否真实生成完整 Plan，必须由下一单一代表验收证明。
