# 项目结构与阅读入口整理

Owner: 当前主代理。基线：develop `01b30e8`；分支：`docs/repository-organization`。

## Goal

消除当前入口与过时说明的冲突，清楚区分当前规格、历史资料、开发工具和本地临时产物，避免重复维护业务规则。

## Constraints

保留原始补充规格、模型路由原文、ADR与验收证据；不操作 .workbuddy/、design-preview/，不读取秘密值、不调用模型provider、不写业务数据库。保留业务代码结构和历史证据路径。

## Allowed changes

README.md、docs 分类导航、scripts/README.md、output/README.md、.gitignore、本任务计划/检查记录；仅移动已确认的未跟踪测试产物到忽略的 output/local-archive/，逐文件核对哈希，不删除内容。

## Non-goals

不重构业务代码/公共契约，不整合 M1.1，不更改历史文件内容，不重写Git历史，不推送/发布，不删除本机环境或缓存。

## Tests

原文与历史证据/业务文件哈希保全；导航本地链接检查；允许范围检查；Git diff检查；临时产物移动哈希核对。业务/大型测试、付费调用 NOT RUN。

## Evidence

一次目录/文档侦察后复用 findings.md；最终记录命令、exit code、结果与迁移映射。

## Rollback

文档使用新的 revert 提交；本地产物按记录的路径映射移回，不覆盖已存在文件。

## Phases

- [x] 核对目录、入口、最新规格及临时产物候选。
- [x] 形成明确的导航和产物归类。
- [x] 执行文档与本地产物整理。
- [x] 离线验证：341个文件保全、7份归档、80个本地链接、允许范围与diff均PASS。
- [x] Git交付：docs/repository-organization正常提交并no-ff集成develop；实际SHA以Git日志及本次交付消息为准。

## Next Step

本轮整理结束；后续业务Goal从develop按实施路线另建短分支。

## Errors Encountered

首次批量读取输出过长，后续按目录及单文件限量读取，避免全仓重复探索。

apply_patch 不支持在同一 patch 对 README 同时 Delete/Add，未应用任何变更；改用 UTF-8/LF 写入 README，其他文件正常补丁更新。
