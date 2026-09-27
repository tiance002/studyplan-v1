# B0 来源溯源：source-provenance

> 产出日期：2026-09-27 · 复核时机：B1 迁入任何模块前必须重新生成本文件
> **目的**：逐个记录 `D:\studyplan` 内每个文件的来源、作者归属与完整性摘要，使「这份文件是谁写的、从哪来、有没有被改过」可被机械验证。
> **方法**：`sha256sum`（大小写敏感、逐字节）。目录 `.venv/` / `.git/` 按 `.gitignore` 排除。

---

## 1. 溯源基线

| 项 | 值 |
|---|---|
| LEGACY_ROOT | `E:\codex_workspace\study-plan` |
| LEGACY HEAD | `1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1` |
| LEGACY 分支 | `codex/v2-clean-baseline-20260925` |
| LEGACY 工作树 | clean（`status --porcelain` 0 行） |
| NEW_ROOT | `D:\studyplan` |
| NEW Git | `master`，**0 commit**（B0 结束时仍为 0 commit，提交由后续步骤完成） |
| 溯源生成工具 | `sha256sum`（Git Bash）/ `find` |

> ⚠️ **关键结论（请先读这条）**：`D:\studyplan` 内的**每一个文件都是新版自研**（origin = `new-authored`），**没有任何一个文件是从 LEGACY_ROOT 复制而来的**。
> 这符合 `module-reuse-matrix.md` §0 的总方针：本批次迁入 **0 个源码文件**。

---

## 2. 逐文件溯源表

字段说明：`origin` = `new-authored`（新版自研）| `legacy-copy`（从旧仓库复制）| `legacy-adapted`（改造自旧仓库）。
`legacy_ref` = 旧仓库对应路径（仅 `legacy-*` 时填写）。

### 2.1 仓库根

| 路径 | SHA-256 | origin | legacy_ref | 说明 |
|---|---|---|---|---|
| `.env.example` | `bbdabbbc065f40a54729e94db9ea92ab4f6288e50b498cc1da72b50e99130e37` | `new-authored` | — | 占位值；`CHANGE_ME` 标记所有需填项。**不含任何旧 secret**（旧 `.env.example` 未读取、未复制）。 |
| `.gitignore` | `71de822fb54845b4af9179e59fea0295a66fa7dfc73edbe783489b05b47418ce` | `new-authored` | — | 覆盖 `.env*` / `.venv` / `node_modules` / `var/` / 旧工具链缓存（`.serena` `.trae` `.codex` `.agents` `.playwright-mcp`）。 |
| `LICENSE` | `c4ac4e3d53dbb2419ca13fb2087e893749c29d1482dcdcf106d634d348475ee8` | `new-authored` | — | MIT。⚠️ 引入 `psycopg`（LGPL-3.0-only）时须额外随附其许可证文本，见 `module-reuse-matrix.md` §2.2。 |
| `README.md` | `a92c32ae957c56ed8e0cc8b9dbc51c0216a9fd5df78fae084e34732a549fe2c3` | `new-authored` | — | 描述 pre-B0 状态、三权威源、关键不变量。 |

### 2.2 `backend/app/core/`（624 行合计）

| 路径 | SHA-256 | origin | legacy_ref | 说明 |
|---|---|---|---|---|
| `core/__init__.py` | `a11fbec7d311ad067f3921a186e8ee96dd4a2695081b34145e14b96995ad47a0` | `new-authored` | — | 重导出 `Settings` / `get_settings` / `ErrorCode` / `AppError` 家族。 |
| `core/config.py` | `3ef92def880530a38561810e360738734cef5943d68291d7317c0b45fd14ae11` | `new-authored` | — | 130 行；唯一读环境变量处；`memory` / `fake` 骨架开关。对比旧 `db/settings.py` **未复制其命名**（旧用 `STUDY_PLATFORM_*` 前缀，新用 `STUDYPLAN_*`）。 |
| `core/errors.py` | `bd56cf878ea58d9b73abbedd1e0050dbda5cd2919c2957a9296e28143ba25b7f` | `new-authored` | — | 119 行；`ErrorCode` 12 值 + `STATUS_BY_CODE`；相对旧 `core/errors.py`(217 行) **重新实现**，未带旧业务错误码。 |
| `core/idempotency.py` | `72fa311b196e1ebdb1fb5c3be91133adc30415fb1b201e1b941aefeef4d945da` | `new-authored` | — | 相对旧 `identity/idempotency.py`(313 行) **重新实现**（见矩阵 §3 C6 关联约束）。 |
| `core/ids.py` | `c090a00cc77035e23949285a59c7f30c7d3fa2ea440f32634f9b3028fe68cb52` | `new-authored` | — | `new_id` / `content_hash` / `slugify_stable_key` / `require_stable_key`。对比旧 `core/ids.py`(26 行) **未复制**（旧无 `slugify_stable_key`）。 |
| `core/request_context.py` | `0a7082cacb356ff64c93d2055a4cd0aff1dafbce5dfb89ac7cb13aab247ce2ed` | `new-authored` | — | 相对旧 `core/request_context.py`(44 行) 重新实现。 |

### 2.3 `backend/app/domain/`（1,863 行合计）

| 路径 | SHA-256 | origin | legacy_ref | 说明 |
|---|---|---|---|---|
| `domain/__init__.py` | `4d0441e884d9bc0a8621abed92c6ab458d0584a01561279fe3ea33272088635e` | `new-authored` | — | — |
| `domain/enums.py` | `48ef494df8e2e8a2c4137bcefe537d838cc6fee3d9b6cc383efc8e22c747af56` | `new-authored` | — | 设计 §8 全部状态枚举。**实测**：`UnitProgress` 4 值、`AiRunStatus` 7 值，与设计一致。 |
| `domain/catalog/models.py` | `79bd9328d50f01682c368ba9ffd561ef7cbfc3560b70b7bcd6096436efa4c8cb` | `new-authored` | — | 旧仓库**无对应模块**（旧无知识节点/关系/单元概念），完全自研。 |
| `domain/planning/models.py` | `02b9641f7664af6f0095f6cf3896a9406e5bb220875545f0f92d6d656fdf8e95` | `new-authored` | — | 相对旧 `product/`(5 文件) **重新设计**：`PlanDraft`/`PlanRevision`/`PlanStage`/`PlanUnitLink`/`PlanTaskLink` + `PlanPublicationService` + `diff_revisions`（按 `stable_key` 精确匹配，不按标题模糊）。 |
| `domain/reflections/models.py` | `6fbf0a95b2f3aaf3e4f8d2f3c31bf0ed795593ce6179a907fe51508c4a8a0281` | `new-authored` | — | 232 行；相对旧 `learning/`(8 文件) **重新设计**；保留「历史不可变提交」思路。⚠️ 未迁入旧掌握度打分。 |
| `domain/resources/models.py` | `3ef9191c27b6f9515b2a8f0de429aba0a30f2aecbe33d7387e2672650ca92beb` | `new-authored` | — | 265 行；`require_safe_url` **实测**拒绝 `http://127.0.0.1/x`（抛 `ValidationAppError`）。旧 `knowledge/fetch_policy.py`(183 行) **未迁入**，仅作思路对照。 |
| `domain/workspace/models.py` | `b873a2dd73ed996f03ce9e76bc0ab13497985503452b2bf6677c30ede62e0961` | `new-authored` | — | 196 行；`AuthContext`（服务端生成）/ `Membership` / `CredentialPolicy(6,12,invite=False)`。**实测** `DEFAULT_CREDENTIAL_POLICY` → `min=6, max=12, invite=False`。 |

### 2.4 本 B0 新增（审计交付物）

| 路径 | SHA-256 | origin | 说明 |
|---|---|---|---|
| `docs/migration/legacy-inventory.md` | `16d698cb9583fab2a8499334e2997964bcc0aa16014ce7a885648c486f1ebc18` | `new-authored` | 本 B0 §1 事实审计 |
| `docs/migration/module-reuse-matrix.md` | `6f7c4c90b0431517d81bb8f09048d6b52b3e5bce891ce1c4d9e9639cd139fa09` | `new-authored` | 本 B0 §2 复用矩阵 |
| `docs/migration/source-provenance.md` | （本文件，自指哈希见下） | `new-authored` | 本文件 |
| `docs/adr/*.md` | 见 `docs/adr/` | `new-authored` | B0 §3 架构决策 |

> 本文件的自指 SHA-256 无法在文件内自洽记录（写入后哈希变化）。复核方式：
> ```bash
> cd /d/studyplan && sha256sum docs/migration/*.md docs/adr/*.md backend/app/core/*.py backend/app/domain/*.py backend/app/domain/*/*.py
> ```

### 2.5 空目录占位（当前无文件，非"缺失"）

以下目录在 B0 时**有意为空**（设计文档 §1 要求的位置已建立，内容待 B1+ 填充）：

```
backend/app/api/v1/            backend/app/application/
backend/app/agent_workflows/   backend/app/infrastructure/{checkpointer,db,external,providers,worker}/
backend/app/ports/             backend/app/domain/practice/
backend/alembic/versions/      backend/tests/{unit,contract,integration,e2e}/
contracts/examples/            docs/{acceptance,adr,design,design-package}/
frontend/src/{api,features/*,shared,styles}/   scripts/   var/
```

---

## 3. 验证方法（可复现）

```bash
# 1) 复核 E 盘未被改动
export GIT_OPTIONAL_LOCKS=0
git --no-optional-locks -C "E:/codex_workspace/study-plan" rev-parse HEAD
# 期望：1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1
git --no-optional-locks -C "E:/codex_workspace/study-plan" status --porcelain=v1
# 期望：(空)

# 2) 复核 D 盘无 legacy-copy
cd /d/studyplan
grep -rn "E:\\\\\|codex_workspace\|tiance002" --include="*.py" --include="*.md" --include="*.toml" \
  --include="*.json" --include="*.ts" --include="*.tsx" . 2>/dev/null | grep -v "docs/migration/" | grep -v "docs/adr/"
# 期望：无输出（迁移/ADR 文档中作为"来源引用"出现属正常，故排除）

# 3) 复核 D 盘可独立导入（不依赖 E 盘）
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'backend'); import app.domain.enums; print('OK')"
```

---

## 4. B1 迁入时的强制记录格式

若 B1 决定迁入任何模块，**必须**在提交说明与本文件中补记以下 6 列，缺一不可（对应 `IMPLEMENTATION_PLAN.md` §0「复制模块时记录 legacy HEAD / 源路径 / 目标路径 / 许可证 / 修改原因 / 测试证据」）：

| 字段 | 示例 |
|---|---|
| `legacy_head` | `1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1` |
| `source_path` | `backend/app/identity/passwords.py` |
| `target_path` | `backend/app/identity/passwords.py` |
| `sha256_src` | `a2a8998a48ff2ce61a500bea86ed50e55d6571e2367660b3a12a04ec71605382` |
| `license` | MIT / Apache-2.0 / CC0（`argon2-cffi` 传递依赖） |
| `modification_reason` | 逐条说明为何必须改（不能写"格式化"） |
| `test_evidence` | 指向本仓库内新增的测试文件与通过记录 |

---

## 5. 已知缺口

1. **本文件的自指哈希缺失**（§2.4）。这是格式固有限制，已给出复核命令代替。
2. **`sha256sum` 大小写敏感**：本文件记录的哈希基于 LF/CRLF 的**实际字节**。⚠️ 若本仓库曾配置 `core.autocrlf`，跨机器复核可能出现差异。B1 应显式设置 `.gitattributes`（旧仓库有该文件，**未迁入**，B1 需自建）以固定换行。
3. **未记录 E 盘全量文件哈希**：任务要求「每项结论有源码/测试证据」，但未要求冻结整个旧仓库。若 B1 需要更强的可比对性，应一次性生成 E 盘 `find -exec sha256sum` 清单存于 `docs/migration/legacy-raw/`（该目录已在 `.gitignore` 中排除）。
