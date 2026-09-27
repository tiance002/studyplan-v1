"""外部适配器：GitHub / RAG / 资源索引。

约束（SOFTWARE_DESIGN.md §6）：外部内容视为**不可信数据** ——
限制 URL scheme、拒绝私网地址与重定向 SSRF、限制下载体积与时长、
不将页面内容提升为系统指令、输出做 XSS 清洗。
**不得自动 clone 并执行外部仓库代码。**
"""

__all__: list[str] = []
