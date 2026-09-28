# B2-C 业务契约收口 —— 验收报告

- **仓库**：`D:\studyplan`（`origin` = `https://github.com/tiance002/studyplan-v1.git`，分支 `master`）
- **审查参考**：`tiance002/studyplan-v1 master@cd08d90620e6bfaaf990bfef5363cb08feb786fa`
- **执行前 HEAD**：`cd08d90620e6bfaaf990bfef5363cb08feb786fa`（与参考**一致**），工作树干净
- **结论**：Goal 六项交付全部完成；**314 测试通过**；`ruff` / `mypy` / 前端 `tsc -b` 干净。
- **未触碰**：旧目录 `E:\codex_workspace\study-plan` 全程**只读未访问**；所有数据库操作仅限
  `studyplan_test_*` 临时库（用后即 DROP）。

---

## 1. 提交列表（每个独立模块一个可回退提交）

| 提交 | 模块 | 内容 |
|---|---|---|
| `75b8674` | B2C-A | 发布携带完整结构 + 废弃只回 `draft_ref` 的不完整编辑（P1-01 / P1-04） |
| `8953f73` | B2C-B | 迁移 `0003`：复合 project FK + 字段对齐 + 公共资源/主线/扩展表（P1-02 / P1-03 / P1-07） |
| `ed11e05` | B2C-C | 主线/扩展确定性校验接入发布边界 + 公共资源/领域包单测 |
| `bc0eece` | B2C-D | 真实 PG 端口契约 `PgPlanRepository`（幂等/并发/回滚） |
| `dbbb214` | B2C-E | `/api/v1` 业务 DTO + OpenAPI 导出 + 前端类型生成 |

> 说明：`75b8674` 在本次会话开始前已完成，其余四个提交在本次会话内完成。

---

## 2. 交付项与达成情况

### §1 完整 编辑→校验→发布→回读（P1-01 / P1-04）

- `PlanDraft` / `PlanRevision` 新增 `unit_links` / `task_links` / `stage_resources` /
  `extensions` / `source_pack_key` / `source_pack_version`；
  `content_hash` 与 `structure_fingerprint` **覆盖全部发布结构**。
- `PlanPublicationService.publish` 把上述结构**全部**传入 `PlanRevision`，并把草案期
  `plan_id=""` 的资源/扩展用 `bound_to_plan()` 重新绑定到新版本（`dataclasses.replace`，
  不改原对象）。
- 编辑契约收口：`REQUIRED_EDIT_KEYS = (nodes, units, relations, practice_proposal)`；
  只回 `draft_ref`（或纯字符串）的编辑结果**直接判为 `failed_validation`**，
  错误信息含「缺少完整草案结构」。旧的不完整兼容**已废弃**。
- 「历史完成记录不丢失」由 `test_republish_preserves_historical_completion_records`
  在真实 PG 上验收：连续发布 rev1→rev2 后 `summary_attempts` 原文仍在。

### §2 迁移 `0003`（不改已发布的 0001/0002）

`backend/alembic/versions/0003_contract_alignment.py`（467 行）：

1. **复合 project FK**（P1-02）：父表加 `UNIQUE (project_id, <id>)`，子表单列 FK 换成
   `FOREIGN KEY (project_id, <id>)`。共 **23 条**复合 FK。RLS 只过滤**行**、不保证 FK 两端
   归属一致；复合 FK 才能在数据库层禁止「本项目引用别的项目的实体」。
2. **字段对齐**（P1-03）：
   - `learning_units` +`objectives`（`rubric` 默认 `'[]'` → `'{}'`）
   - `plan_stages` +`section_kind` / `objective`
   - `practice_projects` +`title` / `version`
   - `practice_tasks` +`title` / `stage_index`
   - `resource_records` +`source_note`
   - `plan_revisions` +`source_pack_key` / `source_pack_version`
   - `plan_publications` +`idempotency_key` / `body_fingerprint` /
     `structure_fingerprint` / `revision`；遗留 `run_id` / `operation_key` 放开 `NOT NULL`
     （新端口契约以 `(project_id, idempotency_key)` 为幂等作用域，否则基础设施无法写入
     纯 `PublishRecord` 形态记录，是 B2-D 的硬阻塞）。
3. **新表**：`domain_packs` / `public_resource_sources` / `public_resource_sections`
   （公共受审核**只读**：FORCE RLS + `FOR SELECT USING (true)`，应用角色仅 `GRANT SELECT`）
   ＋ `stage_resource_assignments` / `knowledge_extensions`（项目 RLS）。
   同 URL 可有多个章节：`public_resource_sections` **不建** `UNIQUE(url)`。
4. **反例**：`tests/integration/test_pg_contract_alignment.py`（25 例）在**拥有 BYPASSRLS
   的迁移角色**下验证跨项目引用仍被拒（证明约束来自 FK 而非 RLS）：
   `knowledge_relations`（from/to 节点）、`unit_node_links`、`practice_tasks` 三处反例 + 同项目正例。
5. **domain/schema 对齐矩阵**：`test_domain_entity_fields_have_columns` 参数化遍历 12 个
   领域实体，逐一断言「领域字段 → 表列」存在——**新增字段忘迁移即失败**。
6. **降级数据保护**：新表任一有行即 `RAISE EXCEPTION '… 拒绝降级'`；空库可干净降级回 `0002`。

### §3 真实 PG 端口契约（幂等 / 并发 / 回滚）

`backend/app/infrastructure/db/plan_repository.py`（629 行，`PgPlanRepository`）：

- `publish_revision` 在**单事务**内完成：置旧版本 superseded → 写 `plan_revisions` →
  写 `plan_stages` / `plan_unit_links` / `plan_task_links` →
  写 `stage_resource_assignments` / `knowledge_extensions` → 更新草案状态 → 写发布记录。
  块内异常由 psycopg 事务边界**整体回滚**，不留半发布状态。
- 幂等靠 **DB 唯一索引** `(project_id, idempotency_key)`，**不**用「先查后写」。
- 所有语句在 `SET LOCAL app.project_id` 下、以**应用角色**（NOBYPASSRLS）执行，
  跨项目读写由 RLS 直接拒绝。
- `save_draft` 按状态过滤：已 `CANCELLED` 的草案不得被覆盖为可发布。
- 结构以**规范化子表**为准；`plan_revisions.structure` 同步写等价 jsonb 快照（审计用，
  非读回依据）；读回按**所属阶段 `order_index`** 排序，保证确定性。
- `approved_at` 无列 → 随 `structure` jsonb 无损保存并读回。

**假仓储 vs 真实 PG 的区分**（明确写进测试模块 docstring）：

| | 位置 | 验证内容 |
|---|---|---|
| 假仓储 | `tests/unit/test_plan_publication.py` | 领域规则与发布**编排**（不碰数据库） |
| 真实 PG | `tests/integration/test_pg_plan_repository.py`（9 例） | **只有数据库能证明**的属性：单事务原子性、DB 唯一约束幂等、并发只有一个事务胜出、RLS 隔离 |

### §4 确定性校验（绝不做重复率计算）

- 领域层 `app/domain/resources/curation.py`：`validate_mainline_continuity`（每阶段至多
  一条 `PRIMARY`；章节引用非空、不重复；同阶段 `order_index` 不重复）、
  `validate_extensions`（主题非空、顺序非负、同阶段顺序不重复、已核验链接过
  `require_safe_url`）、`validate_extension_soft_limit`（**只警告不阻断**）。
- **接线**：`PlanRevision._validate_structure()` 现在会跑前两者（**硬错误，阻断发布**），
  新增 `PlanRevision.validation_warnings()` 暴露软上限警告。
- 「负能力」护栏 `test_curation_module_does_not_compute_duplicate_ratios`：扫描
  `curation` 源码，出现 `overlap_ratio` / `coverage_ratio` / `jaccard` / `similarity`
  等即失败——把「V1 不做重复度计算」固定为可执行约束。

### §5 接口 DTO / OpenAPI / 示例 / 前端生成物

- `backend/app/api/v1/schemas.py`：**23 个业务 DTO**（`RunView`、`PlanView` /
  `PlanDraftView` / `PlanSnapshot`、`StageDetail`、`OrderedSection`、
  `StageResourceAssignmentView`、`KnowledgeExtensionView`、`PracticeTaskView`、
  `DraftDecisionRequest`、`ProgressPatchRequest`、`ErrorBody` 等）。
  - 状态枚举一律**复用** `app.domain.enums`，不在 DTO 另立一套。
  - `AuthContext` **永不**进可写请求体；可选集合字段默认 `[]`（与 `null` 分开）；
    `RunView` 字段闭集，不含图内部节点名。
- `app/main.py` 把 DTO 注册进 OpenAPI `components.schemas`（无路由也能导出契约）；
  具体业务**路由**留给 B2-V。
- `contracts/openapi.json` 重新导出（**35 个 schema**）；
  `contracts/examples/v1_examples.json` 扩到 **16 个示例**并加 `$schema_map`，示例由 DTO
  **机械校验**。
- `frontend/src/api/generated/schema.d.ts` 用 `openapi-typescript 7.13.0` 重新生成
  （637 行）；`frontend/src/api/README.md` 更新当前状态。
- `scripts/export_openapi.sh` + `backend/app/tools/export_openapi.py`：确定性契约导出。
- 契约漂移门禁 `test_committed_openapi_matches_fresh_export`：提交物与重新导出**逐字节一致**。

---

## 3. 变更文件（相对审查参考，27 个文件 / +5970 −28）

| 文件 | 说明 |
|---|---|
| `backend/alembic/versions/0003_contract_alignment.py` | **新增** 迁移 0003 |
| `backend/app/domain/enums.py` | +`DomainPackStatus` / `StageResourceRole` / `ResourceSourceVisibility` |
| `backend/app/domain/domain_packs/{__init__,models}.py` | **新增** `DomainPack` |
| `backend/app/domain/resources/curation.py` | **新增** 公共资源/章节、阶段资源、扩展知识 + 确定性校验 |
| `backend/app/domain/resources/models.py` | `ResourceRecord.project_id` 改为必填（P1-07） |
| `backend/app/domain/planning/models.py` | 完整发布结构 + 指纹覆盖 + 校验接线 + `validation_warnings()` |
| `backend/app/agent_workflows/nodes.py` | 严格编辑契约（缺结构即失败） |
| `backend/app/infrastructure/db/plan_repository.py` | **新增** `PgPlanRepository` |
| `backend/app/infrastructure/db/__init__.py` | 导出仓储 |
| `backend/app/api/v1/schemas.py` | **新增** 23 个业务 DTO |
| `backend/app/main.py` | 注册 DTO 进 OpenAPI |
| `backend/app/tools/{__init__,export_openapi}.py` | **新增** 契约导出工具 |
| `backend/tests/unit/test_plan_publication.py` | +发布完整结构 RED 测试 |
| `backend/tests/unit/test_graph_workflows.py` | +严格编辑契约测试 |
| `backend/tests/unit/test_domain_invariants.py` | +`ResourceRecord` 必填 `project_id` |
| `backend/tests/unit/test_resource_curation.py` | **新增** 25 例 |
| `backend/tests/integration/test_real_langgraph.py` | 适配完整草案结构 |
| `backend/tests/integration/test_pg_contract_alignment.py` | **新增** 25 例 |
| `backend/tests/integration/test_pg_plan_repository.py` | **新增** 9 例 |
| `backend/tests/contract/test_v1_dto_contract.py` | **新增** 8 例 |
| `contracts/openapi.json` | 重新导出（35 schema） |
| `contracts/examples/v1_examples.json` | 16 示例 + `$schema_map` |
| `frontend/src/api/generated/schema.d.ts` | 重新生成 |
| `frontend/src/api/README.md` | 更新当前状态 |
| `scripts/export_openapi.sh` | **新增** 契约导出脚本 |

---

## 4. 执行命令与退出码

| 命令 | 退出码 | 结果 |
|---|---|---|
| `alembic upgrade head`（临时库 `studyplan_test_verify0003_*`） | 0 | `alembic_version=0003`；5 张新表、23 条复合 FK、字段对齐列、RLS/策略全部就位 |
| `alembic downgrade 0002`（同上临时库） | 0 | 新表删除、字段复原、`plan_publications` 回到 7 列 |
| `pytest backend/tests/integration/test_pg_contract_alignment.py` | 0 | 25 passed |
| `pytest backend/tests/unit/test_resource_curation.py` | 0 | 25 passed |
| `pytest backend/tests/integration/test_pg_plan_repository.py` | 0 | 9 passed |
| `pytest backend/tests/contract/test_v1_dto_contract.py` | 0 | 8 passed |
| `pytest`（全量） | 0 | **314 passed in 138.36s** |
| `ruff check backend/` | 0 | All checks passed |
| `mypy backend` | 0 | no issues found in **49** source files |
| `bash scripts/export_openapi.sh` | 0 | 写入 `contracts/openapi.json` |
| `npm run gen:api`（frontend） | 0 | `openapi-typescript 7.13.0` 生成 `schema.d.ts` |
| `npx tsc -b`（frontend） | 0 | 前端类型检查通过 |

### 测试分布（314）

| 层 | 文件 | 数量 |
|---|---|---|
| unit | test_domain_invariants | 30 |
| unit | test_evidence_grade | 20 |
| unit | test_graph_workflows | 31 |
| unit | test_import_direction | 6 |
| unit | test_plan_publication | 27 |
| unit | test_plan_validators | 25 |
| unit | test_resource_curation | 25 |
| unit | test_security_boundaries | 13 |
| contract | test_contract_consistency | 15 |
| contract | test_isolation_contract | 7 |
| contract | test_v1_dto_contract | 8 |
| integration | test_app_boot | 6 |
| integration | test_graph_recovery_pg | 5 |
| integration | test_pg_business_schema | 6 |
| integration | test_pg_contract_alignment | 25 |
| integration | test_pg_harness_safety | 10 |
| integration | test_pg_migration_rls | 12 |
| integration | test_pg_plan_repository | 9 |
| integration | test_real_langgraph | 25 |
| integration | test_startup_guard | 9 |

> `postgres` 组在本地 PG 可达时**真实运行**（本次未跳过）：本机 `127.0.0.1:5432`
> 可用，且 `studyplan_migrator` / `studyplan_app` 两个角色已存在且属性满足要求，
> harness 因此**不修改任何角色**（未设置 `STUDYPLAN_TEST_PG_DEDICATED`，走「已存在即保留」路径）。

---

## 5. 未运行项

| 未运行 | 原因 |
|---|---|
| 具体业务**路由**（`/api/v1/*`） | Goal 明确「可按后续 B2-V 实现具体路由」；本批次只交付**契约模型** |
| 前端 UI / 交互 | 前端可独立推进；本批次只更新生成类型（`tsc -b` 已通过） |
| `npm run build`（vite 产物构建） | 只做了类型检查；产物构建非本批次验收项 |
| 真实云模型调用 | 全程 `LLM_PROVIDER=fake`，不产生外部费用与凭据依赖 |
| 高并发 / 大规模压测 | 设计明确「延后，但不延后租户/幂等/事务正确性」；本批次已覆盖幂等/并发正确性（2 线程竞态） |
| `RepositoryPort` 其余域的 PG 实现（catalog / practice / reflections / resources） | 非 B2-C 范围；B2-D 只实现了发布路径所需的 `PlanRepositoryPort` |
| 认证（P1-05） | 该缺陷本身**被阻塞**，非本批次重点；`Actor` / `Membership` 表仍未建 |
| CI 流水线 | 仓库无 CI 配置；漂移门禁已以测试形式提供（`test_committed_openapi_matches_fresh_export`） |

---

## 6. 已知非阻断问题（登记，不影响 B2-V）

1. **`approved_at` 无独立列**：`plan_revisions` 建表时未包含该列，现随 `structure` jsonb
   无损保存/读回。若将来需要按审批时间查询或索引，应加列（属新迁移）。
2. **`structure` jsonb 与规范化子表并存**：两者由同一事务、同一来源写入，当前不会分叉；
   但存在「未来写入者只更新其一」的隐患。建议在 B2-V 决定其一为唯一真相（倾向子表），
   或补一条一致性断言。
3. **`prompt_revisions` 命名错位**：领域字段 `revision_no` vs 列名 `revision`；表还含
   领域上属于 `PromptExport` 的 `export_text`。**未修**——不影响 B2-V（发布路径），
   属独立的 Prompt 工作台契约整理。
4. **`plan_stages.stage_id` 为全局主键**：每次新版本必须**重新生成阶段 ID**，
   因此 `diff_revisions` 类实现**不得**假设 `stage_id` 跨版本稳定，必须用 `stable_key`
   匹配（领域侧已如此设计）。
5. **`resource_records` 表多出 `created_at` 列**（领域 `ResourceRecord` 无此字段）：
   冗余但无害，属单向多列。
6. **`PracticeProject.version` / `PracticeTask.stage_index` 已补列但无 PG 仓储写入**：
   实践域仓储实现属 B2-V/后续；领域侧已在使用这两个字段。
7. **并发测试规模有限**：仅 2 线程同键竞态，验证「恰好一个胜出」。更大并发压力留待压测批次。
8. **`contracts/openapi.json` 无业务路径**：`paths` 仍只有 `/healthz`，前端目前只能生成
   **类型**、不能生成 client 方法——符合「路由留待 B2-V」的约定。

---

## 7. 下个 Goal 建议：**B2-V 薄垂直切片**

建议范围（在 B2-C 已冻结的契约之上，不再改结构）：

1. **打通一条端到端路径**：`POST /api/v1/plans/generate` → `GET /api/v1/runs/{run_id}`
   → `POST /api/v1/plans/drafts/{draft_id}/decision` → `GET /api/v1/plans/current`。
   应用层用 `PgPlanRepository` 包裹事务；草案/发布复用 B2-C 已验证的领域规则。
2. **`ai_runs` 投影接线**：把图执行状态映射为稳定 `RunView.status / next_action`
   （前端永不接触 Checkpoint / 节点名）。
3. **资源与扩展落地**：把 `stage_resource_assignments` / `knowledge_extensions` 从
   `GET /plans/current` 输出为 `StageResourceAssignmentView` / `KnowledgeExtensionView`
   （`ordered_sections` 保序、`fallback_search_terms` 代替假链接）。
4. **修复 §6 第 3 条**（Prompt 工作台命名错位）与补 `approved_at` 列（可选）。
5. **进入 B2-V 前先加 RED 测试**：HTTP 层契约测试（`TestClient` + 真实 PG），
   证明「编辑 → 校验 → 发布 → 回读」在 HTTP 边界上完整。
