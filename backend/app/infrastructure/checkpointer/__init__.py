"""Postgres Checkpointer bootstrap。

约束（ADR-0002 / SOFTWARE_DESIGN.md §5）：

- 独立数据库 `studyplan_checkpoint` 与独立角色；
- `.setup()` 由**受控 bootstrap 执行**，不在应用启动路径隐式建表；
- 生产使用 `PostgresSaver` / `AsyncPostgresSaver`，
  **不得**使用仅驻内存的 Saver；
- `LANGGRAPH_STRICT_MSGPACK=true` 必须在 import langgraph **之前**生效
  （见 `app/agent_workflows/_msgpack_guard.py`）。

本项目**只保存工作流执行位置**，不保存业务事实。
"""

__all__: list[str] = []
