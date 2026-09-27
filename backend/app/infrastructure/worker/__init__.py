"""后台 worker：队列领取与图驱动。

约束（SOFTWARE_DESIGN.md §5）：

- 使用 lease + `claim_token` fencing + 唯一 job key；
- 恢复后**必须重新查** Run / attempt 当前状态，不能凭旧内存状态推进；
- 同一线程并发恢复**串行化**；
- 已 dispatched 且上游结果未知的付费调用**不自动重发**。
"""

__all__: list[str] = []
