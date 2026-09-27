# src/api

## 唯一职责

存放**由 OpenAPI 自动生成**的 TypeScript 客户端与类型。

## 铁律（ADR-0004）

1. **不要手写**这里的类型。契约真相源是后端的 Pydantic 模型。
2. 生成命令：`npm run gen:api`（读取 `../contracts/openapi.json`）。
3. 生成物提交入库，并由 CI 校验「重新生成后无差异」以发现契约漂移。
4. 前端**不得**自行定义业务状态枚举 —— 从生成类型里取。

## 当前状态

B1 骨架：待 B2 产生业务路由后，`contracts/openapi.json` 才会包含业务路径。
