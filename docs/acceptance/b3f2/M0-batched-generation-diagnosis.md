# B3-F2 分批生成：M0 诊断

检查日期：2026-09-29。基线 HEAD：`ce7a749782ee5127ef2d9603d3c42471a1f4705d`。
工作树原有未跟踪目录 `.workbuddy/`、`design-preview/` 不在本轮范围。
本轮没有调用真实模型、没有改写业务库、Checkpoint 或历史 Attempt。

## 已确认事实

| 检查项 | 当前证据与结论 |
|---|---|
| 默认输出预算 | `core/config.py` 的 `LLM_MAX_OUTPUT_TOKENS` 默认 8000；部署装配和个人模型装配均传入该值。 |
| HTTP 请求 | `openai_compatible.py` 直接使用 `max_tokens=self.max_tokens`；四种 purpose 共用预算，没有阶段配置。 |
| 思考模式 | 当前 b3f2-v2 仅在 hostname 为 `api.deepseek.com` 且模型名精确为 `deepseek-flash` 时发送 `thinking: {type: disabled}`；其他服务不发送。其他模型名不满足条件，不能声称也关闭了思考。 |
| 历史差异 | `git show ce7a749^:backend/app/infrastructure/providers/openai_compatible.py` 为 b3f2-v1，无 thinking 控制，检测 length 时直接返回失败，尚未读取 usage。 |
| 失败 JSON null | 同版本 `attempt_ledger.py` 使用 `asdict(result) if isinstance(result, LLMResult) else None`，再写入 Jsonb；失败因此保存为 JSON null。 |
| 当前失败持久化 | ce7a749 改为所有结果均 `asdict(result)`；截断失败能保存计量、finish_reason、model_id 和两个字符计数。历史 null 原样保留，读取时使用旧失败兼容路径。 |
| 尚缺可观测性 | 成功响应缺少 usage 时仍使用 `or 0`；实际 max_tokens/thinking 未保存在结果中；非 JSON 的失败没有完整 finish/count 诊断；预算未参与请求指纹。 |
| 流程失败传播 | 真 Graph 和解释器均串联 outline → structure → practice，直到 practice 后才检查 generation 错误。 |
| Outline 输入 | goal、prefs、完整 domain_pack。 |
| Structure 输入 | goal、完整 outline、完整 domain_pack，一次要求全部 nodes/units/relations。 |
| Practice 输入 | goal、完整 outline、全部 nodes/units、完整 domain_pack。 |
| Repair 输入 | goal、全部本轮结构错误、完整 outline/nodes/units/relations/practice 和完整 domain_pack。最多两次，但修复范围未限制。 |
| 恢复边界 | `PgPlanningExecutor.execute` 对已有 checkpoint 一律拒绝重新生成；需要明确可恢复的中途 checkpoint 与已失败/等待确认的区别。现有账本对未知派发结果禁止重复派发。 |

## 离线复现：FAIL（现有行为违背目标）

使用临时内存 Probe，所有 purpose 返回 `LLMFailure('provider_output_truncated', ...)`，通过当前 `run_planning_graph` 执行；不写库、不联网。

命令：从仓库根目录使用 `.venv/Scripts/python.exe -`，脚本先执行 `sys.path.insert(0, 'backend')`，注入 Probe 到 PlanningNodes，输入非空学习目标。

原始输出：

```text
{'calls': ['planning.outline', 'planning.structure', 'planning.practice'], 'stopped_at': 'failed_validation'}
```

纲要已经失败，后两个请求仍会执行。这是可直接复现的额外调用原因。

## 模型能力与历史证据边界

2026-09-29 官方文档公开显示 `deepseek-flash` 支持关闭思考；Chat Completions 的 max_tokens 最大值 393216，未设置时非思考模式默认 8K。本项目显式传入预算，因此不能把服务商默认值当作实际请求值。能力上限不等于本项目应使用的预算；分阶段方案使用远低于上限的配置。

来源：[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)、[模型说明](https://api-docs.deepseek.com/quick_start/pricing/)。本次仅查询公开文档，没有调用账户模型接口。

历史 run `run_54bd4bd11b6047709c581a3e530d43b6` 的三个失败、NULL 计量和 JSON null 只证明程序记录了截断。已有验收文件记录当时配置为 8000，但没有保存每个 HTTP 请求体、原始响应或真实用量，不能据此证明每次消耗或截断发生在思考还是正文。高思考与单次整条路线是风险因素，具体历史原因仍不能完全证实。

## 状态

- PASS：静态版本差异核对；无网络离线复现。
- FAIL：当前失败立即停止、阶段分批、完整计量诊断未达到新目标。
- NOT RUN：新实现测试、真实 DeepSeek 验证。
