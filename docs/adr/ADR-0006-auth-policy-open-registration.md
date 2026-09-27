# ADR-0006：认证保持「开放注册 / 中文用户名 / 6–12 位密码 / 无邀请码」

- **状态**：Accepted（B0 冻结，已在本机核实）
- **日期**：2026-09-27
- **关联**：`IMPLEMENTATION_PLAN.md` §0 §2、`SOFTWARE_DESIGN.md` §3 §10
- **用户既定**：开放注册，中文用户名，密码 6–12 位，无邀请码；以 E 盘当前最终实现为准核实。

## 背景

本机审计发现旧仓库的认证经历了**一次完整的回退与重建**：

- `main`（`0d31e54`，2026-09-21）时代存在**邀请码兑换链路**。
- 2026-09-25 的一组提交将其**整体删除**：
  - `508a694` Remove invitation flow and converge auth on password sessions
  - `16c868d` merge: remove the invitation chain and converge auth on passwords
  - `8226ff1` Rebuild password validation as a single 6-12 code point policy
  - `6ca82b3` feat(frontend): drop invite auth and unify password policy to 6-12
  - `d6af3d9` Drop the invite chain from round8 tools and deployment config
  - `6398650` test(tools): remove invite flow from round8 browser and gate scripts
- 末版（HEAD `1c1b1c8`）实测：`grep -i "invit"` 在 `backend/app`、`frontend/src`、`alembic` 中**零命中**；`alembic/versions/0001_initial_schema.py` docstring 明写「唯一的结构性删减是**邀请码全链路**（新版只保留用户名 + 密码）」。

**风险**：这组提交**大部分在未推送的本地分支上**（10 个分支无 upstream），而 `origin/main` 停在 09-21 的邀请码时代。任何以 GitHub 默认分支为参考的实现都会**把邀请码恢复到新版**。

## 决策

新版认证严格遵守用户既定约束，**并明确禁止任何形式的邀请码回归**：

| 约束 | 取值 | 本机证据 |
|---|---|---|
| 注册 | **开放注册**，无邀请码 | `grep -i invit` 零命中；0001 docstring |
| 用户名 | 支持**中文**（CJK 扩展 A `\u3400-\u4DBF` + 基本区 `\u4E00-\u9FFF`），首字符须为字母或汉字 | `identity/passwords.py::_USERNAME_ORIGINAL` |
| 用户名归一化 | NFKC + casefold，原值用于展示、归一值用于精确查找 | `normalize_username()` |
| 密码长度 | **恰好 6–12 个 Unicode 码点**（按码点计数；不 strip / 不截断 / 不大小写 / 不 NFKC） | `MIN_PASSWORD_LENGTH = 6` / `MAX_PASSWORD_LENGTH = 12` |
| 密码散列 | **Argon2id**，`memory_cost=19456, time_cost=2, parallelism=1` | `identity/passwords.py::ARGON2_PARAMETERS` |
| 限流 | **必须实现**（任务书：「密码仍须使用安全散列、限流和合理存储」） | 旧 `identity/rate_limit.py`(128 行) 作 reference；新版 B1 自研 |
| 非法输入 | 含**孤立代理项**的口令必须被拒为 `ValueError`，**不得**让 Argon2 抛未捕获 `UnicodeEncodeError`（那会把"口令非法"变成 500） | `validate_password()` 显式 `encode("utf-8")` 捕获 |
| 防枚举 | 未知用户也执行一次等价 Argon2 工作 | `DUMMY_PASSWORD_HASH` |

**从旧代码转写为新版验收条目**（详见 `module-reuse-matrix.md` §3）：

- **C1**：6–12 码点，按码点计数，不做任何归一化。
- **C2**：注册、登录校验、重哈希**共用同一策略入口**，禁止双分支。旧代码 docstring 记录了该事故：「两套策略并存会让"注册能设的密码登录时被拒"或"重哈希对合法密码抛错"」。新版 `domain/workspace/models.py::CredentialPolicy` 是单一入口，**实测** `min=6, max=12, invite=False`。
- **C3**：未知用户走 `DUMMY_PASSWORD_HASH`，防用户名枚举。
- **C4**：认证失败**不区分原因**（格式错 / 签名错 / 过期返回同一种错误），避免给攻击者探测信号。
- **C5**：`AuthContext` **只能**由服务端从可信会话生成，**任何地方不得从请求字段拼装**。

## 后果

**正面**

- 产品约束被固化为常量 + 测试，不依赖记忆。
- 邀请码在物理上不可达（新仓库独立 Git，见 ADR-0001），不存在误 revert 路径。
- 单一策略入口消除了"注册能设、登录被拒"这类跨端点不一致。

**负面 / 代价**

- 6–12 位密码上限**低于**常见安全建议（如 NIST 建议至少 8 位、上限至少 64 位）。这是**用户明确既定**的产品约束，本 ADR 记录该取舍但不改变它。**补偿措施**：强制 Argon2id 高成本参数 + 登录限流 + 常数时间校验，使在线暴力破解不经济。
- 支持中文用户名使用户名归一化（NFKC/casefold）成为安全关键路径，必须有测试向量冻结行为。
- 旧 `identity/` 15 文件 / 1,898 行**不迁入**（其会话载体是 Bearer，新版要 Cookie），因此限流、会话、Cookie 需 B1 **自研**。这是本 ADR 的主要成本。

## 拒绝的备选方案

| 方案 | 拒绝理由 |
|---|---|
| 从 `origin/main` 取认证实现 | `origin/main` 停在邀请码时代，会**恢复已删除的邀请链** |
| 保留邀请码作可选功能 | 违反用户既定「无邀请码」 |
| 沿用旧 Bearer token 会话 | 设计 §7 要求签名 Cookie + CSRF/Origin 处理；载体不同 |
| 沿用旧「注册 6–12 / 登录 12–128」双分支 | 旧代码已记录该分支导致的事故，且已被删除 |
| 把密码上限提到 128 | 违反用户既定约束（6–12） |
| 使用兼容旧邀请数据的双模式 | 设计 §2 明文禁止「为兼容已放弃的旧业务数据构建长期双模型/双 API 兼容层」 |
