# Planning V2 Item 4 — Resource Gap Extraction

日期：2026-10-08。本轮只实现 `CapabilityPlan + CoverageResult → ResourceGapSet` 的确定性领域转换，不搜索资料、不调用产品模型、不生成课程或接线 Runtime。

## 1. 基线与修改范围

- Branch：`feat/n1-resource-discovery`。
- Start HEAD：`2ef6f2ac16b4bc35a1bf1a826b3febcff4db406f`，与预期一致；开始 tracked tree clean，没有未知源码修改。
- 权威：[Planning V2 架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md) Item 2/3/4、Single Authority 与 Producer / Consumer Matrix。复用已有 `capabilities.py` 和 `content_coverage.py`，没有重新设计上游对象或更改审核映射。
- Final HEAD 是包含本报告的本地提交，可用 `git log -1 --format=%H -- docs/planning-v2/ITEM4_RESOURCE_GAP_EXTRACTION.md` 定位；精确 SHA 同时记录在最终答复及 ignored `var/planning-v2-item4-implementation-20261008/final.json`，避免报告自包含 commit SHA。
- 提交消息：`feat(planning): add v2 resource gap extraction`。不 push、merge、deploy。

| 修改文件 | 职责 |
|---|---|
| `backend/app/domain/planning/resource_gaps.py` | 冻结 ResourceGap/ResourceGapSet、纯函数 extract、输入结构及 hash 绑定校验 |
| `backend/tests/unit/test_resource_gaps.py` | 本轮定向行为、真实本地 MCP 索引接口与输入损坏反例 |
| 本报告 | 字段、代表结果、验证与剩余信任边界 |
| `docs/implementation/progress.md` | 仅前置追加本轮结果，保留历史正文 |

没有修改 Item 1/2/3、Policy v2、GoalProfile、审核映射或内容；没有 Application Service、Provider、Repository、API、Worker、流程引擎、UI、数据库表或 migration。既存 `.workbuddy/`、`design-preview/` 未访问、修改或提交。

## 2. 最终字段与转换规则

入口：`extract(capability_plan: CapabilityPlan, coverage_result: CoverageResult) -> ResourceGapSet`。两个输入均为现有冻结领域对象，没有新增序列化解析器或 client DTO。

| 对象 | 字段 |
|---|---|
| ResourceGapSet | `source_capability_plan_hash`、`source_coverage_result_hash`、`gaps[]`；计算属性 `result_hash`、规范化 JSON `to_payload()` |
| ResourceGap | `capability_id`、`missing_outcomes[]`、`importance`、`desired_depth`、`requirement_refs[]` |
| missing_outcomes 项 | 复用 Item 2 `LearningOutcome(outcome_id, text)`；ID 和学习目标文本精确取自冻结 Plan |

只遍历 `CapabilityPlan.learning_capabilities`。full 不生成 gap；partial 仅提取 missing；none 将全部 missing 合并为同 capability 的一个 gap。accepted_known 永不产生资料需求。没有 gap score、confidence、类型、关键词、资源候选、数量或阶段建议。

`learning_requirement` 原值映射为 `importance`，`desired_depth` 与 `requirement_refs` 原值保留；不扩大 recommended，不删除 required，不根据缺教材降深度。仅课程政策引入的系统性 MCP 可没有直接 requirement_refs，仍保留 required gap。全部 full 或 B 集合为空时，`gaps=[]` 正常成功。

结果按 capability_id、missing outcome_id 规范化排序，字段内容不改写；hash 复用既有 `canonical_json/content_hash`。输入对象不变，不创建新的教学资产或任何持久化记录。

## 3. 输入完整性与信任边界

复用 Item 3 已有冻结 Plan 结构检查，核对当前 Policy v2、定义/学习文本、route/depth outcomes、A/B 与既有前置/引用规则，不读取 raw goal 或重建 Profile。

Coverage 必须是当前冻结 `CoverageResult` 类型，并引用同一个 Plan 的规范化 hash；校验内容索引版本引用、hash 形状、规范化结果 hash，以及 entries 与 B 集合精确一致。covered/missing 必须是合法当前 outcome IDs 的完整不相交分区，无多余、重复、过期或遗漏，状态必须与分区相符。结构不一致明确 `ValidationAppError`，不自动补全、修正或重判 coverage。

内容引用只作冻结类型、身份/版本/hash 结构及 outcome 归属的一致性检查；不会读内容索引、源文件、正文或重新裁决 reviewed。内容索引版本是 Item 3 提供的非空冻结引用，不新增版本注册表或把索引绑定到当前 loader。完整索引 hash 的重算、审核资格与教材语义仍属于 Item 3。

Plan/Coverage 的 hash 在既有合同中是计算属性，而非独立存储的客户端字段。入口核对 canonical 重算与属性一致及来源绑定；带 claimed hash 的原始 dict 不作为合法领域输入，不会忽略其 hash 后继续执行。测试显式模拟错误 computed hash，并验证拒绝。hash 证明规范化身份，不能证明来源真实性或检测拥有完整合法重算能力的伪造者。

原 Profile 未随这两个输入传入；原 requirement/claim 事实与未知领域 evidence.input_hash 对原 Profile 的真实性绑定继续由 Item 2 上游保证。没有假称 Item 4 可以只靠 hash 重新证明这些事实。

## 4. full / partial / none 代表结果

| 输入 | Coverage | ResourceGapSet |
|---|---|---|
| MCP：narrow_goal + foundation，Item 3 既有真实本地索引 | full：roles、interfaces 全覆盖 | gaps 空 |
| MCP：narrow_goal + applied，同一索引 | partial：roles、interfaces covered；minimal_connection missing | 一个 MCP gap，只含 minimal_connection 的原 ID/文本；已覆盖理论目标不加入 |
| Tool Calling 与其 llm.api 真前置，合成零映射索引 | none | 一个 Tool Calling gap，包含 input_validation、invoke_result 两个原 ID/文本；llm.api 也精确保留其自身 missing |
| 已知 Python + 待学习 JSON CLI | Python 为 A，JSON CLI none | 仅 JSON CLI gap，无 Python 教材需求 |
| 系统性 MCP policy-only、project_usage=excluded | MCP 学习 required，requirement_refs 空 | required 与深度原样保留；不因项目排除或 refs 空丢失学习 gap |
| 全部 B full / 没有 B | full / 空 entries | 合法空 gaps，不制造 Item 5 工作 |

真实接口测试只复用 Item 3 已固定的 `load_reviewed_content_index()`：agent.application/v8、MCP10.2 source version 2，两概念 mapping。没有新的正文审核、网络读取或审核资格声明。上游 Plan 用已有离线 fixture 构造；这不证明 Item 1/2 产品模型语义。

## 5. 与 Item 5 的接口

未来 Item 5 只消费每项 gap 的 capability_id、精确缺失 outcome ID/文本、required/recommended、desired_depth 和 requirement_refs，据此限制研究范围与预算优先级。两个 source hash 保留到冻结的 Plan 与 Coverage 的追溯绑定。空 GapSet 不产生资料需求。

本轮不实现 Item 5 Consumer、预算决策、搜索关键词、研究候选、Reader 或 ResourceResearchResult；也不重新把 covered outcomes、A 类能力或项目背景变成搜索需求。

## 6. RED / GREEN 与独立审查

| 检查 | 结果 |
|---|---|
| extract stub 行为 RED | FAIL，28 项、0 errors/skip，均进入 NotImplementedError；编码前失败证据保留 |
| Item 4 定向 GREEN | PASS，28 项，包括两个真实 MCP 索引接口实例 |
| 必要 Item 3 hash/validator 及 fail-closed 回归 | PASS，6 项 hash/validator、2 项 generate/submit_generation；统一定向共 36 PASS，0 FAIL/ERROR/SKIP |
| 同范围 import/collection、Ruff、git diff --check | PASS，collection 36；Ruff 仅新增模块及测试，完整 diff 检查通过 |
| 独立审查 | PASS，无剩余 BLOCKER；未为形式复核重复执行测试 |

新测试覆盖两个真实本地 MCP 接口实例、Tool Calling 合并、A 排除、重要性/深度/政策空 refs、合法空结果、来源/计算 hash、旧版本/改写文本、重复/过期/额外/遗漏/交叠 ID、状态与引用版本失效、确定性及输入不变。通过故意破坏冻结状态验证 consumer 明确拒绝，避免构造器去重后把损坏数据误当成有效反例。

使用 `.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit` 运行新文件及指定相邻节点，XML/log 保存在 ignored `var/planning-v2-item4-implementation-20261008/`；Ruff 只检查新增模块和测试。没有重复完整 Backend 或 Item 1/2 历史回归。

相邻节点为 `test_content_coverage.py::test_result_validator_rejects_incomplete_or_tampered_partition`（5 个参数）、`::test_stable_sorted_result_hash_and_serialization_with_frozen_inputs`（1），以及 `test_planning_legacy_removal.py::test_generation_rejects_before_run_job_binding_provider_or_plan_access`（2）。完整规范化三类代表输入/输出留在 ignored `examples.json`，独立审查存于 `independent-review.md`。

独立审查确认：required missing 无遗漏、A 与 covered 无回流、文本/深度/重要性/空 refs 精确保留；结构检查没有重新判断教材审核资格，也没有把两个输入的 hash 冒称为完整 Index/Profile 真实性证明。实现仅一个纯领域模块，没有额外服务、表、Provider 或流程抽象。

主协调请求 `gpt-6.1-sol/high`，纯领域实现与独立审查复用 `gpt-6.1-sol/medium`；实际模型解析均 **NOT OBSERVABLE**，没有修改全局配置或使用 Sol max/HARD 升级。

## 7. 边界保护与未验证项

817 个受保护 tracked 文件、378 个账本文件、`.env` 及原 progress 正文保持；旧 Item 3 报告、审核映射、Policy 与架构合同不变。产品模型 **0**、搜索 **0**、Reader **0**；历史账本 183/280 和 unknown177/183 未操作或重派。

没有 DB/Run/Job/Draft/Plan mutation 路径，公开 generate 保持 fail-closed。真实 PG 与行计数、浏览器、产品模型、外部搜索/接口、正文审核、全量 Backend、整链 E2E 均 **NOT RUN**；不虚报这些层的验证结果。Item 1 CONDITIONALLY_ACCEPTED 与 Item 2 待整链真实语义验收的限制仍保留。

最终：`PLANNING_V2_ITEM4_RESOURCE_GAP_EXTRACTION_COMPLETE`；`ITEM5_NOT_STARTED`；STOP。
