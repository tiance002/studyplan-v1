# 模型路由、许可与预算

2026-10-01 / S0。复用现有 LLMPort、个人模型配置、planning_budget、provider Attempt ledger；不先建设复杂 Router。此处是目标契约，新增隐私字段尚未实现。

## 三层职责

| 层 | 任务 | 执行边界 |
|---|---|---|
| L0 | scope/权限、Schema、状态机、查询、准确命令、幂等、预算 | 确定性代码，不调用模型 |
| L1 | 确有收益的分类/query rewrite/短摘要/低风险问答 | 本地模型可选适配；失败不静默转云 |
| L2 | 规划、复杂问答、反馈、实践/方案比较、调整、成果分析 | 云模型；调用前授权/隐私/预算 Gate |

任务明显需要推理时直接 L2；无授权则请求用户决定或明确能力限制。证据不足是 RETRIEVAL/Evidence 问题，不通过更强模型替代事实。

## CallPolicy（应用层目标输入）

- allow_cloud：是否允许本次任务调用云 provider。
- allow_external_data：是否允许本次任务获取/引用外部数据；不代替私有内容外发许可。
- privacy_scope：project/session 范围、可外发的数据类别和来源集合。
- budget：每 purpose input/output 限额、最大请求/repair、任务累计 token/可配置费用上限。
- purpose、scope、consent_ref：用途、服务端归属、可审计授权来源。

policy 由服务端根据用户设置和本次决定构造，模型不能扩大许可；每次 dispatch 再核对。allow_cloud=False 或包含未获外发许可的私有内容时，请求数必须为 0。本地失败→显示失败/可选云端建议→用户明确允许→新有界云调用；不无感知降级。

开发验收的 ConfirmPaidRun 一次性授权不等于产品长期外发许可；产品明确触发操作也不授权 AI 开发代理额外跑付费测试。

## 当前已验证规划配置

deepseek-flash / api.deepseek.com；thinking disabled；outline 4096、structure 8192、practice 4096、repair 8192；正常 19 请求、最多 21、最多 2 repair。版本 b3f2-batch-v1 / prompt b3f2-v7-practice-repair。此配置是已核对验收基线，非所有未来任务的固定配额。

JSON 合法不等于业务有效；已知内容错误进入有限局部 repair；finish_reason=length 明确截断失败；transport unknown 保持 dispatch_unknown/reconciliation_required 且不 retry。保存 model/prompt/schema、预算、token、延迟、finish_reason 和安全错误分类，不记录凭据。

新任务输出 Schema、许可/预算和最大步数在其 Goal 开始前冻结。高费用验证由用户单独授权、新 AcceptanceId/专用 Project 执行。
