# src/api

## 唯一职责

存放**由 OpenAPI 自动生成**的 TypeScript 客户端与类型。

## 铁律（ADR-0004）

1. **不要手写**这里的类型。契约真相源是后端的 Pydantic 模型。
2. 生成命令：`npm run gen:api`（读取 `../contracts/openapi.json`）。
3. 生成物提交入库，并由 CI 校验「重新生成后无差异」以发现契约漂移。
4. 前端**不得**自行定义业务状态枚举 —— 从生成类型里取。

## 当前状态

B2-C：`contracts/openapi.json` 已包含 `/api/v1` **业务接口模型**（`PlanView` /
`PlanDraftView` / `RunView` / `StageResourceAssignmentView` /
`KnowledgeExtensionView` / `PracticeTaskView` 等），可生成 typed client。

具体业务**路由**由 B2-V 实现；在此之前前端可依据 `contracts/examples/v1_examples.json`
（由 DTO 机械校验）先写 Mock，UI 确认后不应重做后端状态模型。

重新生成：`bash scripts/export_openapi.sh && npm run gen:api`。
