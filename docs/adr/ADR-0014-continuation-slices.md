# ADR-0014：续接切片与临时模型授权

日期：2026-10-02。依据：用户提供的[续接计划](../implementation/STUDYPLAN_CONTINUATION_PLAN_2026-10-02.md)及[新 Goal](../implementation/STUDYPLAN_CONTINUATION_GOAL_2026-10-02.md)。

2026-10-03 追加决定：用户已说“恢复原计划”，下文临时模型档位授权终止，恢复[原动态路由](../execution/model-routing-policy.md) Sol/high、Sol/medium、Luna/max。6Astra 停用仍有效。快速服务模式请求结束，但没有工具切换证据，不宣称主会话模型或服务模式已切换。仅恢复开发执行偏好；当前成果派生切片、交付Goal及外部操作/额度门禁继续有效。

N0 实测 HEAD 为 `cf1537040bbf8c52469e00461723f70726f5a3b2`，分支 `feat/v2-g1-user-slice`，固定点祖先检查 PASS。工作区只有禁止操作的 `.workbuddy/`、`design-preview/` 未跟踪目录。迁移 head 为 0023。

按用户批准的一次性例外，从该当前成果派生 `feat/n1-resource-discovery`，父线暂为 `feat/v2-g1-user-slice`。切片门禁满足后 no-ff 合入父线；累计门禁满足后才集成 develop；master、milestone 仍等待负责人接受。不得回退到较旧 develop/master、覆写更新或修改已发布迁移。

临时开发模型授权：gpt-6-luna 全部实际可用档位；gpt-6.1-sol 除 max 的实际可用档位；gpt-6-astra 仅 low/medium/high。直到用户说“恢复原计划”。派发显式 model/effort，运行解析未提供时记录 NOT OBSERVABLE。最多三活动子代理、两名业务/内容写入者（包括主协调）；主协调整合公共契约、迁移编号、锁顺序与事务模型。不修改全局配置。

首批新增收费模型/Tavily调用为零。公开 GitHub 外发先预约，搜索沿用累计账，内容/元数据独立追加账。上限新增 3/9/6，不重置旧额度、不重派 unknown。现有产品 UI、密码规则及阶段自动完成规则继续生效。整体 NOT_READY。
