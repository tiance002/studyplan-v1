"""HTTP 接入层（`/api/v1`）。

设计约束（SOFTWARE_DESIGN.md §7 / ADR-0004）：

- 唯一前缀 `/api/v1`，项目内路径 `/api/v1/projects/{project_id}/...`。
- **`AuthContext` 永不出现在可写请求体**：由服务端从 Cookie / 签名会话派生。
- Pydantic 模型是**契约真相源**；导出的 `openapi.json` 是派生物。
- 统一错误体 `{code, message, request_id, details}`，不回显敏感输入。

⚠️ B1 阶段尚未实现业务路由（属 B2）。本包目前只放置契约与骨架。
"""

__all__: list[str] = []
