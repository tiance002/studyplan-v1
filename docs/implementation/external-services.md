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

2026-10-02用户询问工程位置与运行状态后，本轮进行了只读定位：独立工程为 `E:\RAG quention`，Docker Compose工作目录 `E:\RAG quention\deploy`、配置 `deploy\compose.yml`；`D:\codex-rag-tools` 是工具/实验目录，不是服务工程。三个既有实例均运行且 `GET /openapi.json`、`GET /healthz` 返回HTTP200，无检索、问答、模型调用、配置修改或重启：

| Docker API实例 | API地址 | 对应前端 |
| --- | --- | --- |
| raglocalfirst0930-api-1 | http://127.0.0.1:18086 | http://127.0.0.1:14186 |
| deploy-api-1 | http://127.0.0.1:18087 | http://127.0.0.1:14187 |
| ragv1final0927-api-1 | http://127.0.0.1:8000 | http://127.0.0.1:4173 |

本机接口快照为 `E:\RAG quention\contracts\openapi.json`，运行说明为工程根 `README.md`，在线文档可从对应API的 `/docs` 或 `/openapi.json` 查看。当前在线OpenAPI公开知识库/文档/会话消息/Run引用接口，没有独立纯检索端点，也未声明securitySchemes；所查当前源码为单机个人工作台，不能假设通用 `RAG_API_KEY` 已受支持。需要先确认保留实例及服务端授权映射、证据检索契约，再决定StudyPlan适配和凭证类型；用户不需要发送模型key或RAG秘密。F17仍BLOCKED，真实检索、跨账号拒绝和故障验收NOT RUN。用户可只打开三个前端，反馈哪一套是自己常用且资料正常的实例；无需新上传、提问或重启。

三实例健康响应均为 `data.status=ok`、`cloud_enabled=false`、`local_query_enabled=false`：服务监听正常，健康检查不证明问答/检索可用；不为探测开启模型或云端许可。

## 已运行证据与余额

专用隔离G1验收实际执行模型20次（含1repair），G3总结反馈1次、Prompt反馈已知HTTP400失败1次及新成功1次；累计 **23/50**，有结果23、未知0。Tavily预检和G2实际页面各一次HTTP200、各1credit，累计 **2/1000**。G2 request_id `6cbd7349-21f3-43a4-91a5-aaf32207d55c`。三项搜索配置足够，不需另装SDK或搜索模型。后续切片不重置额度。详情见[G1报告](../acceptance/G1-v2-user-slice-2026-10-01.md)、[G2资源报告](../acceptance/G2-resources-2026-10-01.md)、[G3总结报告](../acceptance/G3-summaries-2026-10-01.md)与[G3 Prompt报告](../acceptance/G3-prompts-2026-10-01.md)。失败请求不退还本轮请求额度；未返回usage时不猜费用。

产品0013的计数器按单部署数据库持久累计，所有账号共用，不因请求失败退还；0禁用派发，最高1000。验收另沿用.git/v2-search-quota-20261001，在每个真实HTTP前独占预约，跨隔离库累计已有2次，不能用新库计数0重置本轮授权。重复同键只读已有状态，结果未知保留记录，不自动重派；正常只读恢复可按幂等键GET查询。

## GitHub连接体验与待配置入口

连接需求：用户点击连接，浏览器进入GitHub登录/授权页，回调后软件显示已连接账号，可断开。推荐现有应用实现有界GitHub App授权及只读资源适配，按账号加密保存token、只取用户允许的仓库。账号连接不等于允许私有内容发给云模型，仍需对应许可。

GitHub提供[远程MCP与宿主集成说明](https://github.com/github/github-mcp-server/blob/main/docs/host-integration.md)：宿主仍须处理OAuth/回调/token及工具范围。使用远程服务无需本地安装完整GitHub服务，但仅增加MCP配置不代表软件已有连接功能。当前Goal不新增通用平台MCP Runtime；浏览器授权可用GitHub App+API完成。官方[GitHub App用户授权流程](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app)说明client ID、client secret和callback。

后续应用维护者注册App并配置client ID/client secret/固定callback URL，普通用户只做浏览器授权。具体环境变量和回调路径在实现契约确定后写入.env.example，当前尚未接线。现有`GITHUB_TOKEN`仅为历史服务端字段，不作为所有用户共享账号连接；公开候选和手动URL接入可先独立实现。

用户已在官网看到搜索消费，确认密钥有效；无需为此重复发送搜索。GitHub维护者配置入口是GitHub账号 **Settings → Developer settings → GitHub Apps**。这里注册本软件的App、取得Client ID、创建Client secret并登记与后端实现完全一致的Callback URL。普通用户无需填写这些维护者凭证，只在浏览器确认自己的账号和仓库授权。当前Callback路由和App配置尚未实现，不填写猜测的回调地址；也不把Codex插件的凭证或账号连接复制给本软件。

2026-10-02 G3/F10手动实践变更实际Chrome+HTTP+保留PG PASS，新模型请求0、搜索0；累计仍23/50和2/1000、unknown0。专用验收无模型Worker且阻断外部派发，只有预览/明确确认普通事务，不创建付费Run或沿用旧Acceptance journal。详见[G3实践报告](../acceptance/G3-practice-changes-2026-10-02.md)。

2026-10-01续接核对官方用户授权文档：GitHub App的浏览器流程支持S256 PKCE；授权请求携带随机state与固定redirect_uri，回调校验state后用code、client_secret和code_verifier换取用户token。用户token权限是用户与App权限的交集，访问仓库也取双方可访问仓库的交集；App安装与账号授权须分别显示。后续薄集成依此实现服务端一次性会话绑定与按账号加密存储，不由前端存token，也不把手动URL或OAuth页面打开当作连接成功。此为下一实施契约的来源核对，当前账号连接仍未实现，实际授权验收NOT RUN。[GitHub官方授权流程](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app)
