# ADR-0004：`/api/v1` 为唯一契约源，Pydantic / OpenAPI 驱动 TypeScript 客户端

- **状态**：Accepted（B0 冻结，B1 实现）
- **日期**：2026-09-27
- **关联**：`SOFTWARE_DESIGN.md` §7 §10、`IMPLEMENTATION_PLAN.md` §3 §4

## 背景

旧工程的路由形态（本机审计）：

- 旧 API 文件 9 个（`auth_routes` / `library_routes` / `product_*_routes` / `projects_routes` / `routes` / `teaching_routes`），**无 `/api/v1` 前缀**（精确挂载前缀 `unverified`，本 B0 未逐条读取全部装饰器）。
- 旧前端是 **CDN 单页 HTML**（`frontend/src` 下 `.ts/.tsx` = 0 个，无 vite / 无 typescript / 无 build script），通过手写 `api-client.js` 访问后端，**接口形状靠人工同步**。
- 因此旧系统里「后端返回什么」与「前端以为返回什么」之间**没有机械约束**，只有约定。

新版要求：React + TypeScript + Vite，前端**仅使用 OpenAPI 生成的 typed client**，且「不能自行定义业务状态、Graph 内部节点或自报用户/租户身份」。

## 决策

1. **唯一前缀 `/api/v1`**，项目内路径 `/api/v1/projects/{project_id}/...`。不暴露旧的无前缀路由，也不允许两套含义不同的路径（例如两个 `/plan/generate`）共存。
2. **Pydantic 模型是契约真相源**。FastAPI 导出的 `openapi.json` 是**派生物**，不是手写的。
3. **TS 客户端由 OpenAPI 自动生成**（`openapi-typescript` 或同类），提交到 `frontend/src/api/generated/`，由 CI 校验「生成结果与提交内容一致」以发现契约漂移。
4. **`AuthContext` 永不出现在可写请求体**：它由服务端从 Cookie / 签名会话派生，作为应用服务的第一入参。任何把 `actor_id` / `tenant_id` 放进请求 DTO 的设计都被拒绝。
5. **fixture 也由 DTO 校验**：`contracts/examples/` 下的每个 JSON 示例必须能通过对应 Pydantic 模型验证；示例不是"手写的假数据"，而是契约的可执行样本。
6. **统一错误体**：`{code, message, request_id, details}`，`message` 不回显敏感输入（原文总结、完整 Prompt、密钥、token）。`code` 为稳定枚举，前端按 `code` 分支，**不解析 message**。
7. **变更纪律**：API 变更必须**同时**更新示例、文档和双方测试；只改后端不改示例视为未完成。
8. **`operationId` 唯一性**：OpenAPI 中不得有重复 `operationId`（B1 验收条款明确要求）。
9. **`expected_version` / 幂等键**：所有变更操作需携带其一（按操作类型规定）。同键同体返回同结果，**同键异体 409**。
10. **分页 / 排序 / null 语义固定**：固定分页与排序；`null` 与 `[]` 语义明确区分；字段有上限；时间为 UTC ISO8601。

## 后果

**正面**

- 前端类型错误在编译期暴露，而不是运行时。
- 契约漂移可被 CI 机械检出，不依赖评审者记忆。
- 前端可安全重写（换组件库、改布局），只要不改契约就不会破坏后端。

**负面 / 代价**

- 生成客户端引入了构建步骤与一个额外依赖。
- 契约变更需要「改后端 → 重新导出 → 重新生成 → 提交两者」四步，比手写慢。**缓解**：`scripts/` 提供一条命令完成 export + generate + verify。
- B1 需为 `AuthContext` 的注入写专门的「非法身份字段必须被拒绝」测试（设计 §9 API 层要求）。

## 拒绝的备选方案

| 方案 | 拒绝理由 |
|---|---|
| 沿用旧无前缀路由 | 与设计 §7 直接冲突；且旧路由语义新项目不适用 |
| 手写 TS 类型 | 旧系统正在为此付代价：无机械约束，靠人工同步 |
| 前端自报 `tenant_id` / `actor_id` | 等于把认证降级为客户端声明，是越权漏洞的常见成因 |
| 同时保留新旧两套 API | 会出现两套含义不同的同名路径；兼容层是长期负债 |
| 用 GraphQL | V1 不需要，且 Pydantic/OpenAPI 与 FastAPI 栈天然契合 |
