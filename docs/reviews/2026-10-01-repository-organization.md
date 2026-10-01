# 项目结构与阅读入口整理记录

日期：2026-10-01。基线：本地 develop `01b30e8`；整理分支：`docs/repository-organization`。仅记录本地状态，不宣称该提交已存在于 GitHub。

## Goal / Constraints

整理文件入口和本地输出，消除根 README 与 S0 规格的冲突。保留当前权威规格、原始补充、开发路由原文、ADR、历史验收与业务代码；不操作 .workbuddy/、design-preview/，不调用 provider、不写业务数据库。

## Allowed changes / Non-goals

变更根 README、.gitignore、docs 分类导航、scripts/README、output/README、本次计划与记录；归档确认的未跟踪测试产物。业务代码、契约、迁移、依赖、已有证据路径和功能分支不变；不集成 M1.1、不删重复证据、不删除内容、不推送、不发布。

## 整理结果

- 根 README 改为个人本地 V1 概览、实际 develop 状态和阅读入口。将完整业务说明链接到所属规格，不再重复旧注册政策、固定三图和 B0–B6 排期。
- docs/README 按阅读目的与目录职责导航；development、acceptance、execution 分别提供开发、证据、Codex 路由入口。
- scripts/README 区分启动、离线检查、数据库操作和真实模型副作用。保留既有脚本名与实现，明确旧 inspect-live 工具会写 journal/evidence。
- output/README 区分已跟踪截图与忽略的本机输出。7份旧测试产物收至 output/local-archive/2026-10-01，保持原文件名及 archive 子路径；不上传内容。
- .gitignore 去除重复 .mypy_cache 项，新增仅覆盖本地输出的忽略规则。以后临时产物优先写 output/local/。

当前规格、历史计划、验收快照职责不同；文件名相似不构成删除理由。字节扫描只发现两份已跟踪日志完全相同：`docs/acceptance/b3f2/M5-lint.txt` 与 `docs/acceptance/b3f2/live/Offline-lint.txt`，两者属于不同验收批次，均保留。

## 本机归档映射

JSON 结构包含 content/date/start_time/total_suite/status/status_list/total_tests；HTML 包含 pytest 标识。仅读取类型与哈希，不将报告内容写入新文档。以下哈希为 SHA256，移动前后核对一致。

| 原路径 | 归档路径 | SHA256 |
|---|---|---|
| `output.json` | `output/local-archive/2026-10-01/output.json` | `BB811F7DA044AB580FF084485A76FF95A69BE70A34C430317C2BE899D3F4CC94` |
| `pytest_html_report.html` | `output/local-archive/2026-10-01/pytest_html_report.html` | `09FCEC159291BBED8C8D8C605C97533944B74AA2A92091DD97C894145BDCE8D7` |
| `archive/output_1790768084.0023496.json` | `output/local-archive/2026-10-01/archive/output_1790768084.0023496.json` | `F20AAC63CF7CB745F2A7A6220F9CD635B260DF1AFD51E2857F5F87DCF4056985` |
| `archive/output_1790768136.907722.json` | `output/local-archive/2026-10-01/archive/output_1790768136.907722.json` | `80FA4C07EE3C2388A9F4E7A7266930A1C1F5DC7BE8937C08DA5E5E66E6035D47` |
| `archive/output_1790768137.9530704.json` | `output/local-archive/2026-10-01/archive/output_1790768137.9530704.json` | `E4D351BDA78509A1BDE59E2916432F372A3F8B810A24AEC18779C2287D6B35F3` |
| `archive/output_1790768138.3761816.json` | `output/local-archive/2026-10-01/archive/output_1790768138.3761816.json` | `E51E5E414718EF5B76904792651C72523A8334CA1B084A69E5C85FB0A5641064` |
| `archive/output_1790768212.2056084.json` | `output/local-archive/2026-10-01/archive/output_1790768212.2056084.json` | `32217C6ACA84CECE382FC79909F43F43C7388F1FFEF0EB2898ADCD682B14BD28` |

## Tests / Evidence

验证脚本保存在忽略的 `var/repository-organization/verify.py`，不进入产品代码。命令：`.venv/Scripts/python var/repository-organization/verify.py`；另检查 staged diff 与允许路径。最终实际结果记录在本文件末尾。

基线快照有343个已跟踪文件，除计划修改的README与.gitignore，其余341个逐文件核对字节保全。导航检查只验证本次新增/修改Markdown的本地链接，不声称已修复所有历史文档。未改变原始业务输入，既有昂贵业务验证不重跑。

业务测试：NOT RUN。完整/浏览器测试：NOT RUN。付费模型验证：NOT RUN。

实际离线检查 exit code 0：341个基线文件字节保全 PASS；7份本地产物路径/哈希/ignore规则 PASS；80个新增或修改文档的本地Markdown链接 PASS；允许变更范围、当前/历史入口区分和 `git diff --check` PASS。根README由158行减至56行。提交前 staged diff 与12个允许文件核对 PASS。

## Rollback

文档通过新的 revert 提交撤销本次整理；本机产物按上表从归档路径移回原路径，目标若已存在则先核对并停止覆盖。移动记录还保存在忽略的 var/repository-organization/artifact-moves.json。不回滚业务数据、不重写Git历史。
