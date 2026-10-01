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

Tavily 请求入口为 `POST https://api.tavily.com/search`，使用 Bearer key。适配器固定 `search_depth=basic`、`auto_parameters=false`，不自动升级搜索深度；依据 [官方 Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)。**G2已接通显式用户搜索、最多5候选、私有单元选取与刷新回读，并完成真实Tavily+HTTP+PG+Chrome验证。** 结果仍为未核验候选，不新增平台 MCP 或运行外部代码。

模型配置继续使用现有 `LLM_PROVIDER`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL_ID`；账号个人模型设置优先，未配置个人模型时冻结已配置的部署模型。冻结后配置轮换须明确失败，不能悄悄替换队列中 Run 的模型。

免费预检发现现有部署输出上限为 8,000，而默认 structure/repair 目标为 8,192。专用验收将这两项目标限定为 **8,000**，保持既有部署上限；不修改私有 `.env`。日常运行可在本机明确设置：

```dotenv
LLM_STRUCTURE_OUTPUT_TOKENS=8000
LLM_REPAIR_OUTPUT_TOKENS=8000
```

真实调用使用新 AcceptanceId、专用隔离 Project 和持久派发记录。结果未知时保留证据并暂停核对，既有 Acceptance09、历史 Attempt、Run、Draft 和 journal 不恢复、不批准、不删除。

独立 RAG 的现有配置名为 `RAG_BASE_URL`、`RAG_API_KEY`、`RAG_TIMEOUT_SECONDS`，具体服务契约仍待确认。

## 已运行证据与余额

专用隔离G1验收实际执行模型20次（含1repair），有结果20、未知0；累计 **20/50**。Tavily预检和G2实际页面各一次HTTP200、各1credit，累计 **2/1000**。G2 request_id `6cbd7349-21f3-43a4-91a5-aaf32207d55c`。三项搜索配置足够，不需另装SDK或搜索模型。后续切片不重置额度。详情见[G1报告](../acceptance/G1-v2-user-slice-2026-10-01.md)与[G2资源报告](../acceptance/G2-resources-2026-10-01.md)。

产品0013的计数器按单部署数据库持久累计，所有账号共用，不因请求失败退还；0禁用派发，最高1000。验收另沿用.git/v2-search-quota-20261001，在每个真实HTTP前独占预约，跨隔离库累计已有2次，不能用新库计数0重置本轮授权。重复同键只读已有状态，结果未知保留记录，不自动重派；正常只读恢复可按幂等键GET查询。

## GitHub连接体验与待配置入口

连接需求：用户点击连接，浏览器进入GitHub登录/授权页，回调后软件显示已连接账号，可断开。推荐现有应用实现有界GitHub App授权及只读资源适配，按账号加密保存token、只取用户允许的仓库。账号连接不等于允许私有内容发给云模型，仍需对应许可。

GitHub提供[远程MCP与宿主集成说明](https://github.com/github/github-mcp-server/blob/main/docs/host-integration.md)：宿主仍须处理OAuth/回调/token及工具范围。使用远程服务无需本地安装完整GitHub服务，但仅增加MCP配置不代表软件已有连接功能。当前Goal不新增通用平台MCP Runtime；浏览器授权可用GitHub App+API完成。官方[GitHub App用户授权流程](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app)说明client ID、client secret和callback。

后续应用维护者注册App并配置client ID/client secret/固定callback URL，普通用户只做浏览器授权。具体环境变量和回调路径在实现契约确定后写入.env.example，当前尚未接线。现有`GITHUB_TOKEN`仅为历史服务端字段，不作为所有用户共享账号连接；公开候选和手动URL接入可先独立实现。
