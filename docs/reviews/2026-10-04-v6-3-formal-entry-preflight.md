# RC-A 正式入口只读预检

结论：**SAFE_TO_STAGE**，仅允许进入隔离备份恢复演练。当前正式入口还不能直接承接新三包；不表示产品写入/收费/部署获批。

基线：`feat/n1-resource-discovery`，HEAD `161bacd5fa3e88c566b806697ebe52ef34cb6456`。N0/P0 续接及已有实现复用见 [当前审计](2026-10-04-v6-1-resume-n0-p0-audit.md)。源库连接已验证 `.env` 所指真实数据库；只读事务读取，未启动面向源库的 API/Worker。

## 当前入口

预检时端口5173/5175/5177/5178/8000/8021/8022/8024均无 StudyPlan listener；没有 `app.tools.planning_worker` Worker。原日常前端/API当前停止，不能沿用旧文档PID冒充正在运行。

正常入口脚本 `scripts/b3f1-dev.ps1` 默认API8022、前端5175，前端明确代理到所指定API。API为 `.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8022`；前端为 `npm run dev -- --host 127.0.0.1 --port 5175 --strictPort`。只有显式 `-Worker` 才启动 Worker，只有显式 `-Migrate` 才升级；预检没有执行这些命令。

隔离演练后新增5179/8024，明确标为真实数据副本只读入口，使用当前 feature 的 create_app/current frontend 与本地auth-only写入保护。它不属于已切换的正式入口，也不是旧 owned Acceptance。无 Worker/派发；业务写入403，正常用户名密码登录/退出及GET允许。

## 产品环境事实

| 项 | 实际只读结果 |
|---|---|
| host/port/database/app role | 127.0.0.1:5432 / studyplan_b3_local_48fb59cc / studyplan_app |
| server/schema revision | PostgreSQL16.4 / 0023 |
| repo head | 0024；本轮不新增/改已发布迁移 |
| public表/行数 | 61表 / 1517行 |
| 发布包 | agent.application v1、python.engineering v1 |
| 当前注册表下一包 | AI Fullstack2、Agent5、Cloud2、Python2；保留旧专项 |
| auth users / learning projects | 13 / 18；用户给出的 tiance 账号存在 |
| plan revisions / publications / drafts | 12 / 14 / 16 |
| practice projects / tasks | 14 / 50 |
| summaries / prompt revisions / submissions / acceptance reviews | 0 / 0 / 0 / 0；空历史如实记录，不能伪造非空回读样本 |
| ai runs / jobs / provider attempts | 26 / 9 / 128；保留原状态与历史，不恢复/领取旧任务 |
| provider | openai_compatible / api.deepseek.com / deepseek-flash；密钥仅检查SET，不输出 |
| search | Tavily、配置limit1000；key SET，GitHub token MISSING；本轮未发搜索 |
| RAG | StudyPlan连接配置MISSING；独立服务另见RC-D |

完整源 snapshot 在 ignored `var/v63/formal-preflight.json`，只存计数/服务端行摘要、ACL/RLS/policies/columns摘要与非秘密配置，未读出用户正文。备份是独立受控本地归档，不入Git。

## 上线前明确差异

1. 原产品没有三新包，AI/Cloud会显式Seed unavailable；Agent会选择已发布旧v1。代码最新并不等于内容已经部署。不得偷偷改 registry 回退或自动导入。
2. 实测配置预算门禁 FAIL：LLM_MAX_OUTPUT_TOKENS=8000，但structure/repair=8192；当前真实绑定在dispatch前拒绝。候选staging配置把总cap统一到8192，离线预算门禁PASS；只在计划/进程候选中计算，未写原 `.env`。
3. 当前日常服务/Worker未运行；按用户批准的staging窗口显式启动，不恢复未知任务。涉及旧26 Run/9 Job的Worker开启需先精确资格核查，不能开启全局领取来做smoke。
4. 真实账号登录与页面历史消费尚待用户在副本私下操作；账号存在和数据库恢复相等不能代替正常登录。

数据库不变/完整备份恢复/副本forward与Seed导入 PASS，见 [staging方案](2026-10-04-v6-3-staging-plan.md)。原产品写入/正式入口切换 NOT RUN。本次 preflight 的 SAFE_TO_STAGE 仅表示安全进入副本；当前最终门禁仍 STAGING_BLOCKED / NOT_READY。
