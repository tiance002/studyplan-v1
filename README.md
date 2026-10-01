# studyplan — 个人本地学习规划助手

V1 面向个人本地学习，首个领域是 Agent 应用开发。目标闭环为：生成知识结构与路线 → 用户确认 → 学习与总结 → 反馈与实践 → 提交成果 → 证据核验 → 调整路线。

这是交付目标。完整学习闭环尚未验收，具体完成度以实际代码和验收证据为准。

## 当前基线

截至 2026-10-01，本地 develop 已完成 S0 规格收口，复用已有计划版本、模型设置、前端工作区和分批规划能力。Acceptance09 的真实生成证据核对到 Draft / waiting_user；本次真实批准、发布及完整闭环尚未 Verified。

develop 仍保留旧注册登录入口与基于内容 hash 的知识节点身份。M1.1 本地安全入口实现位于独立功能分支，尚未集成到 develop；随后是 M1.2 稳定知识逻辑身份。不能将目标设计或功能分支状态当成当前基线已交付能力。

开发前从 [项目约束](AGENTS.md) 和 [文档导航](docs/README.md) 开始。当前范围及后续顺序统一查阅 [V1 设计包](docs/design-package/README.md)、[实施路线](docs/design-package/IMPLEMENTATION_PLAN.md) 和 [差距审查](docs/reviews/2026-10-01-v1-gap-analysis.md)。

## 目录用途

| 位置 | 内容 |
|---|---|
| `backend/app/` | FastAPI 接入、Application 用例、Domain 规则、Ports 和 Infrastructure |
| `backend/app/agent_workflows/` | LangGraph 有界编排及现有图协议 |
| `backend/alembic/` | 追加式数据库迁移；已发布迁移不改写 |
| `backend/tests/` | unit / contract / integration / e2e |
| `frontend/src/` | React 界面、业务 features、共享组件和 API 客户端 |
| `contracts/` | OpenAPI、契约示例及前后端共同接口 |
| [docs/](docs/README.md) | 当前规格、决策、操作说明和历史证据 |
| [scripts/](scripts/README.md) | 启动、检查、契约生成和受控验收工具 |
| [output/](output/README.md) | 历史浏览器证据及忽略的本地临时输出 |
| `.planning/` | 按任务分目录的执行计划、发现和进度，不是产品规格 |
| `var/`、`.venv/` | 本机运行数据与 Python 环境，不入库 |

依赖方向为 `api -> application -> domain & ports <- infrastructure`。业务表保存业务事实，checkpoint 保存执行位置，`ai_runs` 提供可授权运行投影。详细边界见 [架构规格](docs/design-package/ARCHITECTURE.md) 与 [ADR 索引](docs/adr/README.md)。

## 本地开发

配置与启动入口见 [开发说明](docs/development/README.md)。在当前 develop 上，既有启动脚本仍对应历史认证入口；本地无登录入口按 M1.1 独立交付，不通过关闭身份或 RLS 检查实现。

已有本机 `.env`、数据库和依赖时，可用两个终端启动 Fake 演示：

```powershell
./scripts/b3f1-dev.ps1 -Demo
./scripts/b3f1-dev.ps1 -Frontend
```

前端默认地址为 `http://127.0.0.1:5173`。环境安装、增量迁移、worker 启动及历史注册流程分别见开发说明。Fake 演示不证明真实模型质量。

日常验证按改动范围选择 Unit → Targeted Integration → Critical E2E，完整验证留到里程碑或相关输入变化时。命令和副作用分类见 [脚本导航](scripts/README.md)，历史结果见 [验收索引](docs/acceptance/README.md)。真实 provider 验证每次需要新的明确授权。

## 文档维护

README 只维护项目概览和入口；业务规则写在所属规格，架构决定写在 ADR，实施细节写在任务计划，验证结论写在验收记录。通过链接引用，避免复制成多份容易过时的说明。

产品内模型调用策略见 [产品 MODEL_ROUTING](docs/design-package/MODEL_ROUTING.md)；Codex 开发模型及子代理规则见 [执行约束](docs/execution/README.md)。两者职责不同。

## 许可证

项目许可证见 [LICENSE](LICENSE)。第三方依赖的许可处理见 [模块复用与许可记录](docs/migration/module-reuse-matrix.md)。
