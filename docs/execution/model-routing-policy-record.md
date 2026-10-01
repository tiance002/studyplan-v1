# 模型路由长期约束保存记录

日期：2026-10-01。

## Goal

将用户附件中的动态模型路由与子代理规则保存为项目后续开发默认约束，并在根 AGENTS.md 建立入口。

## Constraints

保留原文字节；遵守现有 Git、安全、付费调用和产品规格优先级约束。旧批次/三图等风险示例不恢复已取代的产品要求。

## Allowed changes

仅根 AGENTS.md、规则原文、本保存记录及原文目录的 .gitattributes（禁止原文换行转换，保证后续 checkout 仍可按字节核对）。

## Non-goals

不创建静态角色配置，不更改全局 Codex 配置、产品代码、模型供应商配置或数据库；不启动业务实现、不调用真实 provider、不批准 Draft、不发布或推送。

## Tests

原文 SHA256 对比、12章节覆盖、AGENTS 相对链接及动态模型参数检查、原 AGENTS 内容保留检查、Git diff/允许路径检查。

业务测试：NOT RUN。付费模型验证：NOT RUN。

## Evidence

源附件：`C:\Users\22088\.codex\attachments\cd9b9138-0ad5-4331-9524-015dad27620e\已粘贴的文本.txt`。

持久文件：[规则原文](model-routing-policy.md)。根入口：[AGENTS.md](../../AGENTS.md)。源附件与持久文件 SHA256 均为 `49873D25FDFD6AC7FE35D48EB18C87541A94F04516A451CC4378CE2DF4D58C80`。

PowerShell/Git 检查 exit code 0：原文哈希一致 PASS；12章节覆盖 PASS；链接与动态模型参数 PASS；原 AGENTS 内容保留 PASS；允许路径和 `git diff --check` PASS。仅四个文档/原文保存配置文件允许进入提交，已有无关未跟踪文件不纳入。Git 原文 blob 与附件字节一致 PASS，路径级 `-text` 防止 CRLF 自动转换。

文档分支 `docs/model-routing-policy` 从本地 develop 创建，检查后正常提交并以 no-ff 集成到本地 develop。不宣称远端已存在该提交；不集成现有 M1.1 功能分支。

## Rollback

通过新的 revert 提交撤销本次文档集成；不重写已发布历史，不修改业务数据或现有功能分支。
