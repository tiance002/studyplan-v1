"""基础设施层：实现 ports 的适配器。

设计约束：`api -> application -> domain & ports <- infrastructure`。
infrastructure 依赖 ports 与 domain，**反向依赖被禁止**。
domain **不得** import 本包任何内容。

子包：
- `db/`          业务库连接与仓储实现
- `checkpointer/` Postgres Checkpointer bootstrap（独立库/角色）
- `worker/`      队列领取与图驱动
- `providers/`   LLM 适配器装配（唯一出口）
- `external/`    GitHub / RAG / 资源索引等外部适配器
"""

__all__: list[str] = []
