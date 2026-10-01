# 脚本导航

从仓库根目录运行脚本。名称中的 B3/B3-F1/B3-F2 表示引入批次；本次整理保留脚本名与实现，只说明它们的用途和实际操作边界。

## 日常启动与离线检查

| 工具 | 用途 | 操作范围 |
|---|---|---|
| [b3f1-dev.ps1](b3f1-dev.ps1) / `-Frontend` / `-Demo` | 正常API / 前端 / 显式Fake启动 | 读取本机.env，默认API8022/前端5175；前端代理到指定API，不接验收wrapper；页面业务操作仍可能写库 |
| [b3f1-dev.ps1](b3f1-dev.ps1) `-Worker` | 启动现有规划 worker | 根据配置消费任务；真实 provider 模式可能产生付费调用 |
| [b3f1-dev.ps1](b3f1-dev.ps1) `-Migrate` | Alembic 增量迁移 | 数据库写入，按 Goal 授权执行 |
| [test.sh](test.sh) | unit / contract / integration 定向测试 | 缺虚拟环境时会创建并安装 pytest；不包含 e2e |
| [export_openapi.sh](export_openapi.sh) | 从当前 DTO 导出 OpenAPI | 改写 `contracts/openapi.json`，前端生成步骤另行执行 |
| [dev.sh](dev.sh)、[b3-dev.ps1](b3-dev.ps1) | 早期骨架/B3 开发启动 | 历史入口，配置与行为以脚本正文为准 |

已有依赖时，常用定向命令：

```powershell
.\scripts\b3f1-dev.ps1 -ApiPort 8022 -FrontendPort 5175
# 另一个终端；默认不启动Worker或派发模型。
.\scripts\b3f1-dev.ps1 -Frontend -ApiPort 8022 -FrontendPort 5175
.venv/Scripts/python -m pytest backend/tests/unit -o addopts= -q
.venv/Scripts/python -m ruff check backend
.venv/Scripts/python -m mypy backend/app
npm --prefix frontend test
npm --prefix frontend run build
```

这些是命令示例，本文件不表示本轮已运行。PG 集成与 E2E 选择必须符合当前 Goal 的测试范围。

## 有业务或外部副作用的工具

| 工具 | 用途 | 使用边界 |
|---|---|---|
| [b3-setup-local.py](b3-setup-local.py) | 初始化专用本地环境 | 会创建数据库及配置，不用于已有环境的日常启动 |
| [b3f1-browser.cjs](b3f1-browser.cjs) | 历史前端浏览器验收 | 注册独立账号、写入演示业务数据及截图 |
| [b3f2-browser.cjs](b3f2-browser.cjs) | Fake 分批路线浏览器验收 | 注册/生成/确认演示计划，写入验收目录 |
| [b3-verify-live.ps1](b3-verify-live.ps1) | 早期真实 provider 验证 | 可能配置个人模型并调用真实 provider，不作为无授权检查命令 |
| [b3f2-controlled-live.ps1](b3f2-controlled-live.ps1) | 受控真实调用 | 每次新明确授权、ConfirmPaidRun、新 AcceptanceId 和专用 Project |
| [b3f2-live-browser.cjs](b3f2-live-browser.cjs) | 历史真实调用浏览器流程 | 涉及模型 dispatch、live journal 和证据，不纳入整理流程 |
| [b3f2-inspect-live.py](b3f2-inspect-live.py) | 早期 live 结果整理 | 读取数据库，可能补写本地 journal / evidence；并非纯只读检查 |

当前只读 Run 核对工具位于 [backend/app/tools/b3f2_inspect.py](../backend/app/tools/b3f2_inspect.py)，需要明确 actor / project / run 范围。工具存在不代表授权恢复历史 Run 或重派 unknown。

更详细的环境说明见 [开发入口](../docs/development/README.md)；付费与数据操作边界以 [AGENTS](../AGENTS.md) 为准。
