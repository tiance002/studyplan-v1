# B3-F1 启动与环境配置

需要 Python 3.11+、Node 24+（布局单测使用原生 TypeScript stripping）、PostgreSQL、本机 Chrome（浏览器验证）。Python 依赖来自 pyproject 的 dev / postgres / agent extras；浏览器驱动来自 frontend 的 playwright-core。

## 已有本地库

在 `D:\studyplan` 执行：

```powershell
.venv/Scripts/python -m pip install -e ".[dev,postgres,agent]"
npm --prefix frontend ci
./scripts/b3f1-dev.ps1 -Migrate
```

`-Migrate` 只读取 `.env` 的迁移 DSN 并执行 `alembic upgrade head`。本批次新增 0008、0009，未改写 0001–0007。业务数据存在时禁止降级认证表。

两个终端分别运行：

```powershell
./scripts/b3f1-dev.ps1 -Demo
./scripts/b3f1-dev.ps1 -Frontend
```

后端 `http://127.0.0.1:8000`，前端 `http://127.0.0.1:5173`。前端开发代理 `/api` 和 `/healthz` 到后端，同源 Cookie。默认端口若被其他进程占用，应先确认用途，脚本不自动终止外部进程。

打开前端后注册中文用户名、6–12 位密码；创建 Agent 开发目标，生成预设演示草案、修改、确认、进入路径和阶段工作区。关掉并重开后端后会话和业务数据依旧保存在 PG；浏览器刷新保留阶段位置。

## 新环境

复制 `.env.example`，安装依赖，先准备独立 PG 管理实例与 `studyplan_migrator` / `studyplan_app` 角色；应用角色须 NOSUPERUSER / NOBYPASSRLS，无 DDL。不要连接旧工程数据库。新环境可按 `scripts/b3-setup-local.py` 的本地安装说明创建随机新业务/Checkpoint 库；仅清空新环境 `.env` 的 DATABASE_URL 后使用，已有库不得重复建库。

主要配置：

| 变量 | 用途 |
|---|---|
| DATABASE_URL | 应用角色访问新版业务 PG；不能使用迁移角色 |
| STUDYPLAN_MIGRATION_DSN | 独立迁移角色 DSN；可使用 postgresql+psycopg 协议 |
| APP_ENV | 本地 development；生产不能使用 Fake |
| LLM_PROVIDER | fake 本地演示；openai_compatible 使用既有模型配置 |
| SESSION_COOKIE_SECURE | 本地 HTTP 为 false；生产 HTTPS 为 true |
| SESSION_TTL_SECONDS | 默认 1209600 秒，服务端验证到期时间 |
| ALLOW_ORIGINS | 本地须包含 http://127.0.0.1:5173；严格列举受信任源 |
| MODEL_SETTINGS_ENCRYPTION_KEY | 有效稳定 Fernet 密钥；本地只用 Fake 时可设为空，不能留下 CHANGE_ME 占位字符串 |
| CHECKPOINT_DATABASE_URL | 真实模型模式使用独立 Checkpoint 库 |
| LLM_ALLOWED_HOSTS | 真实兼容服务商允许名单 |

`SESSION_SECRET` 仍由生产启动守卫要求；当前随机会话是数据库查验的不透明令牌，不把身份放在 Cookie 中。普通业务写请求无论 CSRF_ENABLED 历史配置如何均校验会话绑定的 X-CSRF-Token，客户端通过 `/session` 读取 Token。

## 验证

```powershell
.venv/Scripts/python -m pytest -o addopts= -q -rs
.venv/Scripts/python -m ruff check backend
.venv/Scripts/python -m mypy backend/app
$env:PYTHONPATH='backend'
.venv/Scripts/python -m app.tools.export_openapi
npm --prefix frontend run gen:api
npm --prefix frontend test
npm --prefix frontend run build
# 两端服务启动后；会注册独立的浏览器验收用户并发布一条 Fake 演示计划
node scripts/b3f1-browser.cjs
```

后端集成测试仅在 `studyplan_test_*` 临时库执行。浏览器演示数据属于新注册验收账号，保留以供复核。截图和尺寸 JSON 位于 `output/playwright/`；不会写入 Cookie、密码散列或模型密钥。
