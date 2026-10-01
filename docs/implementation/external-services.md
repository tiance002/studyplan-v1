# 外部服务配置与本轮调用额度

2026-10-01 用户明确授权：使用已配置模型，累计最多 **50 次请求**；搜索选用 **Tavily**，本轮累计最多 **1,000 次请求**。额度属于本轮验收授权，不表示已经发生调用或允许充值。RAG 配置与公网部署条件仍须分别核对。

## 本机配置位置

实际秘密填写在仓库根 `D:\studyplan\.env`。配置名参考 [`.env.example`](../../.env.example)，不要把 `.env` 提交到 Git 或把密钥发到聊天。现有 [b3f1-dev.ps1](../../scripts/b3f1-dev.ps1) 启动入口读取该文件；直接执行 Python 时需先加载进程环境。

Tavily 在其 [官方控制台](https://app.tavily.com/) 获取 API key，然后在本机填写：

```dotenv
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=填入本机密钥
SEARCH_REQUEST_LIMIT=1000
```

Tavily 请求入口为 `POST https://api.tavily.com/search`，使用 Bearer key。适配器计划固定 `search_depth=basic`、`auto_parameters=false`，不自动升级搜索深度；依据 [官方 Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)。**当前 G1 尚未接入搜索适配器，这三项是已选定的 G2 配置契约；填写密钥不等于功能已验收。** 不新增平台 MCP 或运行外部代码。

模型配置继续使用现有 `LLM_PROVIDER`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL_ID`；账号个人模型设置优先，未配置个人模型时冻结已配置的部署模型。冻结后配置轮换须明确失败，不能悄悄替换队列中 Run 的模型。

免费预检发现现有部署输出上限为 8,000，而默认 structure/repair 目标为 8,192。专用验收将这两项目标限定为 **8,000**，保持既有部署上限；不修改私有 `.env`。日常运行可在本机明确设置：

```dotenv
LLM_STRUCTURE_OUTPUT_TOKENS=8000
LLM_REPAIR_OUTPUT_TOKENS=8000
```

真实调用使用新 AcceptanceId、专用隔离 Project 和持久派发记录。结果未知时保留证据并暂停核对，既有 Acceptance09、历史 Attempt、Run、Draft 和 journal 不恢复、不批准、不删除。

独立 RAG 的现有配置名为 `RAG_BASE_URL`、`RAG_API_KEY`、`RAG_TIMEOUT_SECONDS`，具体服务契约仍待确认。GitHub 候选查询的配置入口是 `GITHUB_TOKEN`，不属于 Tavily key。
