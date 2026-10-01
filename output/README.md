# 输出目录

| 路径 | 用途 | Git 状态 |
|---|---|---|
| `playwright/` | 既有 B3-F1 浏览器验收截图与结果 | 已跟踪历史证据，保持原文件与路径 |
| `local/` | 后续未接受的本机测试输出 | 忽略，不作为正式验收结论 |
| `local-archive/` | 本机旧测试输出的保留归档 | 忽略，不上传内容 |

2026-10-01 整理将根 `output.json`、`pytest_html_report.html` 和 `archive/output_*.json` 收到 `local-archive/2026-10-01/`，其中旧 archive 文件仍保留 `archive/` 子目录。逐文件哈希与路径映射见 [整理记录](../docs/reviews/2026-10-01-repository-organization.md)。

新的正式验收证据按 [验收索引](../docs/acceptance/README.md) 进入所属批次，避免覆盖既有截图、日志或 live evidence。未接受的临时报告不再散落在仓库根目录。
