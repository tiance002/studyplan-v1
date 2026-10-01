# 开发与环境入口

适用入口：2026-10-01 / V2.0。旧启动批次说明保留；当前实现状态见 [进度](../implementation/progress.md)，已配置模型及Tavily入口见 [外部服务](../implementation/external-services.md)。M1.1无登录分支不集成。

## 按目的阅读

| 目的 | 入口 | 适用范围 |
|---|---|---|
| 配置本地 Python / Node / PostgreSQL、启动前后端 | [B3-F1 启动说明](B3-F1-startup.md) | 当前 develop 的既有脚本与认证入口；旧产品定位以新规格为准 |
| 查看正式前端最初交付边界 | [B3-F1 scope](B3-F1-scope.md) | 历史前端批次 |
| 查看分批规划阶段的范围 | [B3-F2 scope](B3-F2-scope.md) | 历史生成批次 |
| 找实际可运行的脚本及副作用 | [脚本导航](../../scripts/README.md) | 当前仓库工具清单 |
| 开始下一个业务 Goal | [实施路线](../design-package/IMPLEMENTATION_PLAN.md) | 当前 M0–M4.5 顺序及切片边界 |

## 配置与产物

从根 `.env.example` 核对配置名，秘密值只在本机配置。应用、迁移和 checkpoint 数据库职责分开；配置安装说明不代表本次任务授权写入数据库或调用 provider。

未接受的测试输出放在忽略的 `output/local/`，需要保留的本机旧输出放在 `output/local-archive/`。正式验收证据按验收报告进入对应批次目录。既有 `output/playwright/` 是已跟踪历史证据，仍按原路径保留。

日常仅运行改动相关检查。完整 suite、浏览器业务写入、迁移和真实模型验收各有独立边界，见脚本导航与 AGENTS。
