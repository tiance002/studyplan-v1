# Codex 项目执行约束

| 文件 | 用途 |
|---|---|
| [根 AGENTS](../../AGENTS.md) | 开发前必读入口：Git、产品权威、安全、验证和模型路由 |
| [模型路由与子代理原文](model-routing-policy.md) | 用户长期执行规则；动态 FAST / NORMAL / HARD、独立子任务、升级和 Evidence Packet |
| [保存与核对记录](model-routing-policy-record.md) | 原文字节、哈希、持久入口及 Git 保存范围 |

开发路由是 Codex 如何分工；[产品 MODEL_ROUTING](../design-package/MODEL_ROUTING.md) 是学习助手如何选择运行时模型、核对许可/隐私/预算。二者各自维护，不合并为一套配置。

原文是长期策略，不创建 Luna / Sol Medium / Sol High 静态角色文件。具体模型参数和工具不可切换时的行为在 AGENTS 入口说明。
