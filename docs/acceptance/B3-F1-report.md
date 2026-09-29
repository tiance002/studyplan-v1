# B3-F1 验收与交付（2026-09-29）

## 结果与范围

基于本地 `f30d194`，在 `codex/b3-f1` 增量实现正式 React 前端与第一条真实产品链路。保留本地尚未落到远端的 B2-V 修复、真实模型 Provider、独立 Checkpoint 和个人模型设置。没有 reset、自动合并或改写远端历史；原有未跟踪 `.workbuddy/` 和 `design-preview/` 保留。

实际演示已完成：注册中文用户 → 创建 Agent 开发目标 → 生成四阶段草案 → 双窗口编辑冲突 → 保留当前编辑 → 显式重载 → 修改 → 确认发布 → 正式学习路径 → 阶段工作区 → 刷新恢复。验证环境为真实本地 PG + 明确标识的 Fake LLM 预设 Agent 场景，本轮未调用云模型。

## 分里程碑证据

| 里程碑 | 交付与验证 |
|---|---|
| M0 | 本地/远端分叉和现有改动已记录于 `docs/reviews/B3-F1-baseline.md`；Downloads 原型原样归档，未使用替代设计 |
| M1 | Argon2id、NFKC/casefold 用户名、6–12 码点密码、孤立代理项拒绝、不回显秘密、PG 持久会话、撤销/过期、HttpOnly/Strict Cookie、Origin/CSRF、双桶持久限流 |
| M2 | AppShell、导航/计划/助手、真正 Pointer Capture 拖动分隔线和六类页面；设计 Token 独立 CSS；React state + 本地布局/位置保存 |
| M3 | 复用五条 B2-V 端点和既有发布事务，hash 原样回传、expected_version、稳定确认幂等键；409 不自动覆盖；生成异常与遗留 running 有明确处理规则 |
| M4 | `/workspace` 聚合当前正式版本的阶段、单元、节点、前置 ID、资源、任务与进度；按发布关联 ID 查询；无标题关联、无假 URL |
| M5 | 真实 PG HTTP 反例、布局单测、浏览器真实操作、三个桌面宽度与额外 390px 窄屏截图、Ruff/mypy/前端 build |

0008 新增认证表，0009 为认证表补 FORCE RLS 和精确查验上下文。已有 0001–0007 迁移没有改写。认证表在无上下文的应用连接中返回零行。注册创建用户和归属空间在同一 PG 事务完成；客户端不自报身份或授权范围。

## 运行恢复

原有生成异常转 failed 的规则继续保留。新反例模拟进程中断后的陈旧 running：下一次读取 Run 使用版本 CAS 转为 reconciliation_required / reconcile；不重复调用模型。预算至少 30 分钟，并随修复次数和模型超时扩大。waiting_user 不因等待时间变长而失效，终态不改写；CAS 冲突重新读取并发完成的状态。

## 实际命令

```powershell
.venv/Scripts/python -m pytest backend/tests/e2e/test_b3f1_access.py -o addopts= -q
# 5 passed，含重启会话/隔离/CSRF、密码限流、默认拒绝/过期/归一化、发布闭环、遗留 running 恢复。
.venv/Scripts/python -m pytest backend/tests/e2e/test_b3f1_access.py backend/tests/integration/test_pg_migration_rls.py backend/tests/e2e/test_b3_closed_loop.py -o addopts= -q
# 修正认证 RLS 后的定向回归：19 passed（此时新增用例尚未全部追加）。
.venv/Scripts/python -m pytest -o addopts= -q -rs
# 完整回归结果见下方最终核验记录。
.venv/Scripts/python -m ruff check backend
# All checks passed!
.venv/Scripts/python -m mypy backend/app
# Success: no issues found in 83 source files
$env:PYTHONPATH='backend'
.venv/Scripts/python -m app.tools.export_openapi
npm --prefix frontend run gen:api
npm --prefix frontend test
# 4 passed：联动、恢复、主画布下限、手动打开面板优先。
npm --prefix frontend run build
# TypeScript + Vite；43 modules transformed。
node scripts/b3f1-browser.cjs
# 注册/编辑/409 保留/显式重载/确认/刷新/所有侧栏联动/专注模式/三种桌面尺寸/390px：通过，pageerror=[]。
```

第一次完整回归为 407 passed / 2 failed，分别是旧开发会话兼容测试和认证表 RLS 规范测试；均已修正。随后完整回归 410 passed，再追加遗留 running 恢复反例并修复。原始日志位于本地忽略目录 `var/b3f1-regression-final.txt`；首次失败日志 `var/b3f1-regression.txt` 仍保留。

## 浏览器尺寸结果

| 屏幕宽度 | 全局导航 | 计划栏 | 无助手主画布 | 助手拖动 |
|---|---:|---:|---:|---:|
| 1440 | 158.39 | 244.80 | 1036.81 | 430 → 520 |
| 1920 | 211.19 | 326.39 | 1382.42 | 430 → 520 |
| 1366 | 150.25 | 232.22 | 983.53 | 430 → 520 |

均无横向溢出；拖动时主画布至少 600px。1366 拖宽后自动收起计划栏，关闭助手恢复此前左侧布局；手动重新打开导航可缩窄助手以保留主画布。非按住左键的鼠标移动不改变助手宽度。计划栏节点、会话、成果标题统一 13px / 600，长标题具备原生 title 提示。

截图与机器结果在 `output/playwright/`：

- `b3f1-login.png`、`b3f1-published.png`、`b3f1-conflict.png`、`b3f1-path.png`。
- `b3f1-workspace-1440.png`、`b3f1-workspace-1920.png`、`b3f1-workspace-1366.png`。
- 三个 `b3f1-assistant-*.png`。
- 学习工作台、知识总结、项目实践、我的会话及窄屏截图；实践截图显示正式关联任务和验收标准。
- `b3f1-browser-results.json`，包含尺寸、恢复、冲突保留与 pageerror 结果。

## 未实现、限制与 NOT RUN

- 助手聊天、正式会话消息、总结写入/评审、实践提交/验收、进度写入：未开放；对应页面使用真实空状态或未开放提示。
- Fake 仅提供预设 Agent 场景验证；不代表任意输入目标的模型规划质量。其资料为搜索建议，未核验，无伪造 URL。
- 同步生成不是异步 worker。陈旧运行进入待核对，需要后续管理流程；不会自动恢复付费调用。
- 个人模型与已保存密钥保留，但本轮真实云模型调用：**NOT RUN**。历史证据不视为本轮新验收。
- 生产 HTTPS 反代 / Secure Cookie 实际部署、外网发布、高并发、RAG：**NOT RUN**。
- 布局与当前阅读位置仅保存在当前浏览器；跨设备阅读位置同步延期为 P2。认证及计划事实保存在 PG。
- 限流为基础 IP + 账号桶；生产反代 IP 可信配置和管理清理需要部署阶段验证。

启动说明：`docs/development/B3-F1-startup.md`。B3-F2 依赖与建议：`docs/development/B3-F1-scope.md`。完成 B3-F1 后停止，不自动进入 B3-F2。

## 最终核验记录

最终命令 `.venv/Scripts/python -m pytest -o addopts= -q -rs`：**411 passed in 239.91s (0:03:59)**，零失败、零跳过。最终前端布局单测 **4 passed**，TypeScript/Vite 构建通过（43 modules），Ruff、mypy（83 source files）、git diff --check 通过。浏览器脚本在最后版本重新执行并返回 exit 0。

精简完整回归原始输出归档在 `docs/acceptance/B3-F1-tests.txt`。本地两端已启动用于复核，后端为显式 Fake 演示；没有进入 B3-F2。
