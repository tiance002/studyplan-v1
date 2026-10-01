# 整理事实

- 根 README 仍介绍旧 V1.1、开放注册、固定三图和 B0–B6，和已收口的 S0 文档不一致；必须改为当前入口和可核对的 develop 状态。
- develop 仍为 S0 业务基线；M1.1代码在独立 feat/m1-1-local-entry，不能借整理将它集成或宣称完成。
- docs/design-package 与 ADR 索引已经区分新规格/旧设计；保持原文路径，新增docs总导航集中阅读顺序。
- docs缺少总入口；验收报告、开发说明和执行路由也缺少分类入口。
- .gitignore 重复 .mypy_cache/；根未跟踪 output.json、pytest_html_report.html、archive/output_*.json 是待核对临时产物。禁止修改live journal/evidence。
- output/playwright 已跟踪截图是历史验收证据，不因为位于output目录而删除或挪动。
- .planning/b2v-b3、docs/superpowers、docs/migration 属于历史计划/溯源，保持原路径与字节。

- 6份JSON的结构字段为 content/date/start_time/total_suite/status/status_list/total_tests；HTML包含pytest标识。确认为本地测试汇总，归档7文件且无删除。不同JSON哈希各不相同。
- 全部docs/output已跟踪内容哈希分组只发现 M5-lint.txt 与 live/Offline-lint.txt 字节相同；属于不同验收上下文，保留各自记录。
- 343个基线已跟踪文件已记录到忽略的 var/repository-organization/baseline-hashes.json，作为本轮保全证据。
- 脚本名称相近但副作用不同：b3f2-inspect-live.py可能补写journal/evidence，真正只读工具是backend/app/tools/b3f2_inspect.py；脚本导航明确区分，不删除所谓“重复”脚本。
