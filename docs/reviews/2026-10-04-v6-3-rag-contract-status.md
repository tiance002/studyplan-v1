# v6.3 RC — RAG 契约只读状态

日期：2026-10-04
结论：**NEEDS_USER_INSTANCE_SELECTION**
模型请求：Luna/high；实际解析值 **NOT OBSERVABLE**。

## 实例与证据

- 精确定位的独立工程为 `E:\RAG quention`，本机目录存在；没有读取 `documents/` 或 ingestion 内容，也没有改项目、配置或服务。
- 当前 Docker inventory 显示 API 容器 `raglocalfirst0930-api-1` 映射至 `http://127.0.0.1:18086`。该端口是检查时唯一监听的三个历史 API 端口；`8000` 和 `18087` 未响应。StudyPlan 根配置未发现 `RAG_BASE_URL` / `RAG_API_KEY`，现有证据无法唯一证明 18086 是用户常用实例，因此需要用户选择。
- 当前 `GET http://127.0.0.1:18086/healthz` 返回 HTTP 200；公开状态为 `ok`、`cloud_enabled=false`、`local_query_enabled=false`。这仅证明健康路由可读，不能证明检索可用。
- 当前 `GET http://127.0.0.1:18086/openapi.json` 返回 HTTP 200，OpenAPI `3.1.0`、服务版本 `0.1.0`，23 paths。在线响应 UTF-8 内容 SHA-256：`C4EC7CFFA3CF6AA25BB64EF49B8DCE2EF964C513CFD63C4B221532BF8B01311D`。工程快照 `E:\RAG quention\contracts\openapi.json` SHA-256：`E29DE9AC6A06C7F3762BA00C7CB4C2B11212C170A5389F4452DEAAB11AF51492`；它与在线文档不同，不能当作当前运行合同。
- 免费本机 HTTP 读取：共 16 次 GET 尝试（health/OpenAPI 路由探测；包括离线端口的失败读取）。无检索、问答、模型、索引、上传或其它带副作用调用；未读取 RAG 私有文档。StudyPlan 调用模型次数为 0。

## 合同核对

| 范围 | 当前在线证据 | 对薄集成的影响 |
| --- | --- | --- |
| 纯检索 | 未见独立 retrieve/search/query endpoint。只有会话消息 `POST /api/v1/conversations/{conversation_id}/messages`（operationId `send_message_api_v1_conversations__conversation_id__messages_post`）及 conversation/run 管理路径。`mode` 是普通 string，没有检索专用枚举或不生成保证。 | 无法证明请求只做检索；不应把消息路径当检索适配器。未调用它。 |
| dataset scope | `ConversationIn` 有 `knowledge_base_scope[]`、`document_scope[]`；`MessageIn` 有 `expected_knowledge_base_scope`、`expected_document_scope`。 | 有 scope 形状，但没有可核实的授权 caller 到 scope 的映射规则、服务端强制语义或越权拒绝合同。 |
| caller / tenant | 请求模型未公开 caller/user/tenant 身份字段；OpenAPI 无全局 security，operation 未声明 security，`components.securitySchemes` 为空。 | 无法证明服务端按 StudyPlan 当前用户/租户授权，或隔离其他用户数据。 |
| auth | 当前在线 OpenAPI 未声明认证方案。 | `RAG_API_KEY` 是否受支持、其主体与范围都未知。不得传 StudyPlan 用户模型密钥，也不能依赖客户端传入身份或 scope 来绕过 RAG 权限。 |
| citation / source identity | 有 `/api/v1/runs/{run_id}/citations/{citation_id}`，属 run 相关接口；没有纯检索返回的证据与来源身份 schema。 | 尚未证明可返回与每条证据绑定、可追溯且稳定的来源 ID/定位信息。 |
| error / timeout | 消息接口 OpenAPI 只声明 201、422；未描述授权拒绝、未知 scope、不可用、限流或上游失败响应。未找到请求 timeout 字段或可依赖的服务 timeout 合同。 | 无法区分授权拒绝与服务不可用，也不能据此配置可靠超时和安全降级。StudyPlan 既有 RAGPort 要求超时/失败显式降级且带 citation。 |

## 决策

用户须先指定应使用的 RAG 实例。实例选择之后，应以该实例当前在线 OpenAPI 重新核对纯检索、服务端 caller/tenant 授权映射、dataset scope 强制规则、citation/source identity、错误与 timeout。观察到的合同缺口如上；本报告结论是实例选择待定，因此不写外部服务修改方案。当前不声明 `READY_FOR_THIN_INTEGRATION`；F17 仍未解除阻塞。
