# Planning V2 Item7 P2 — Draft / Revision 持久化与确认

日期：2026-10-08。P2 独立审查 PASS。

## 基线和调用链

Item7 Start HEAD：`f1f3d139d197c29e8d76a0d5d0ce87a045278f4f`。P2 Start / P1 checkpoint：`52a326b`，分支 `feat/n1-resource-discovery`。用户授权连续实施 P1/P2/P3、独立审查及本地 checkpoint；不 push/merge/deploy，不进入 Item8。实施与独审请求 Sol6.1 xhigh，主协调 Sol6.1 high，实际解析 NOT OBSERVABLE。

`compile_curriculum → PgV2PlanningPersistence.persist → Catalog/实体/links/资源/Draft 单一 PG 事务 → PlanService 编辑重编译/当前 hash 明确确认 → 既有原子 Publication → PgPlanRepository Fresh Readback → Plan/Learning/Practice/Summary/Assistant`。

## 实际持久化与消费者

显式 `V2ExecutionSnapshotV1` 进入 Draft payload / Revision structure 现有 JSONB，字段为 version、compiled、manifest、bindings、compiler_packet、original_curriculum_hash；Domain typed 字段、序列化、当前 hash、Revision fingerprint、Stage ID remap、实际读取全部消费。固定类型解码器不接受 JSON 指定类；恢复重建同一 Compiler 确定性投影并比较整个 compiled/Manifest，不能靠自报 digest 自证。原 Curriculum hash、当前编译 hash、当前 Draft hash 分别保留。合法标题/学习描述编辑重跑 Item6 Validator 和实际 Compiler，不重选能力或资料。

`section_kind=v2_curriculum` 是与合法 typed 快照双向绑定的协议 marker；真实 role/前置单独消费。原列是无 CHECK text，既有 0025 足够，未新增 migration/grant/FK。公共 source 仍只读：public_reviewed 首次绑定独立核查冻结来源、受控 Content JSON 整包 hash/审核记录 hash、实际 catalog 来源/章节字段；不能冻结已替换来源的当前 digest 自证。research_checked 使用项目资源记录和 typed binding，保留字符串版本与资格，实际阅读投影消费，不冒充公共审核来源。精确 Knowledge identity/version/语义匹配才复用，不按标题合并。

默认禁止无 Run 持久化，仅 owned 同步测试显式 allow_unbound_preview。真实 Run 要求当前 actor/project/run/job/lease fence；取消/过期/错误身份拒绝。同键同体幂等、异体拒绝、故障整体回滚。发布沿用单一原子事务、当前版本/CAS/明确用户确认和 current revision 指针；历史不可变，不以最大 revision 推断 current。

| 冻结事实 | 实际承载和消费 |
|---|---|
| Profile 起点、claims、A/B、目标用途、requirements | 完整来源/hash；Draft/Plan v2_content；A 不生成教学实体 |
| Capability/Policy/outcome/depth/importance/真实前置 | 完整 Plan/context/Manifest；Stage/Unit/Task 精确关联及正式投影 |
| Stage title/role/order/why_now/what_to_learn | normalized Stage + typed 映射；Plan/历史 API；1400 字描述无截断 |
| Knowledge/Unit/rubric/Task/links | 实体、精确版本绑定、结构化验收/outcome refs；学习/实践实际消费者 |
| 材料角色/source/section/字符串版本/审核访问限制 | public 和项目资源分开；正式 Stage reading、Learning Exposure |
| Guidance/PracticeDelta/任务增量/保留/复用 | typed 事实 + 原列；实际 PgPrompts/PgSummaries/Exposure |
| 已有项目/Micro Exercise/最终成果 | carrier/task kind/final_artifact；正式 Plan/实践上下文，不覆盖已有项目 |
| whole_core/slices/案例 | 独立 ProjectStudy；两种模式真实 PG round-trip，不混同持续实践 |
| constraints/assessment/unresolved | 完整 hash 保护和校验；未解不能编译；正式解释投影 |
| 私有事实与助手 | 内部 Profile/project_context 不进入公共教学上下文；只投影必要教学要求 |

完整原始字段清点保留在 P1 报告；本表记录实际消费，JSONB 存在本身不代表接线。

## RED / GREEN 和真实 PG

证据：ignored `var/planning-v2-item7-p2-20261008/`。所有 PG 写入只在新 owned `studyplan_test_v2p2_*`，已有角色复用、roles_created=[]、既有 migration0025；每次数据库名存 `owned-database-*.json`，库保留。正式数据、历史 Run/Receipt/unknown 未写入。

| 验证 | 结果 | 证据 |
|---|---|---|
| marker / typed snapshot RED | FAIL（预期2）→ PASS | critical-red/green.log |
| public 首次绑定替换 RED | FAIL（预期4）→ PASS | source-binding-red.log / pg-final.xml |
| compiled/Manifest 一致重哈希分叉 RED | FAIL（预期4）→ PASS | snapshot-binding-red.log / compiler-final.xml |
| 原 Item6 缺空 assessment 代表 RED | FAIL（预期1）→ PASS | historical-snapshot-red.xml / compiler-historical-final.xml |
| 最终 Compiler/Snapshot | PASS（69，含原 P1 62） | compiler-historical-final.xml |
| publication/Validator/Service/Exposure/Prompt/Summary 定向 | PASS（114） | adjacent-unit.xml |
| 真实 PG 整组 | PASS（20） | pg-final.xml / roundtrip.json / fresh-api-*.json |
| 新增真实 Run 当前 fence/幂等/cancel迟到 | PASS（1） | pg-fenced-positive.xml；仅新增定向 |
| 真实 PgBrowserAuth cookie/CSRF/scope、编辑确认/current/history、public503 HTTP | PASS（1） | http-green.xml / http-readback.json；初始 history404 保留 http-red.xml |
| DTO/生成契约/实际 PG 示例 | PASS（9） | dto-final.xml |

PG 覆盖全字段 Fresh Readback、显式发布、同体重放/异体拒绝、保存故障全回滚、编辑后当前 hash 确认、CAS/scope/marker、来源与实体篡改、精确公共知识复用、两次 Revision 历史保持、真实下游消费。HTTP 未覆盖认证 dependency，Provider 为禁止派发 sentinel。Ruff/diff check 结果在最终 checkpoint 记录。不重复全库回归，不能把上述重叠用例累加成全部新增数量。

## 独立审查

fresh-context 独立审查检查实际源码、diff、冻结合同和执行证据，发现并修复：非空 Run 可无 fence；首次 public 绑定可自证替换来源；compiled/Manifest 可一致重哈希分叉。两项来源/快照只读探针修复后拒绝，Run 边界由真实 PG 反例及正例验证。

收口另发现 P1 可编译的历史完整样例在 P2 快照缺空 constraint_assessments 时失败。仅共享 P1 既有规范化：确实无约束且重算为空才补空字段。原 source/hash/样例不改，不豁免非空约束；原完整代表编译 payload/Manifest 逐对象一致，digest 仍 `002f913c52b7a9fbc002c83d4da9948865a3d76fc0d7a2f597db5f4ff42a9ce0`。原 RED 保留，不将失败隐藏。

独立审查最终 PASS，无剩余具体 P2 阻断。审查者自行复现历史样例和四类重哈希反例，并核对最终 XML/真实 HTTP 证据；没有重复全仓审计。最终 Ruff、git diff --check PASS。状态 ITEM7_P2_PERSISTENCE_COMPLETE；按授权连续进入 P3。

## 修改与剩余门禁

新增 v2_execution、v2_planning_persistence、unit/PG/HTTP 测试、本报告；修改现有 Plan Domain/Repository/Catalog/Service/composition、API schema/views/history、Exposure/Prompt/Summary、Compiler 纯映射/规范化复用、OpenAPI/生成类型/真实 PG 示例和 progress。文件逐项以 P2 checkpoint diff 为准。冻结架构、Item1～6核心语义、Policy/Prompt/Schema/审核映射/Seed/迁移未改；原历史证据/.env/样例基线核对。

产品模型、外部搜索、Reader 均0。真实教学质量、未知领域正式网络证据、浏览器、全产品端到端 NOT RUN；审核身份机械检查不证明教材语义正确。Run 成功不等于 Plan 发布，不替用户自动确认。P3 Worker/Receipt/Checkpoint/共享预算恢复待实施；正式 generate 继续关闭。
