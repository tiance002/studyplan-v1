# ADR-0008：工作流按业务边界演进，State 使用候选引用

- 状态：Accepted（S0目标设计），新图/State实现待后续切片。
- 取代：ADR-0005 的“永远恰好三图/不得第四图”数量限制；保留唯一编排引擎、业务/断点分离、有限步数、授权、幂等与未知副作用不重派。
- 关联：[ARCHITECTURE](../design-package/ARCHITECTURE.md)。

## 决策

Planning/Learning/Reflection/Practice/PlanAdjustment为职责边界；不是立即创建五图的要求。复用现有图，只有多步外部推理任务需要图；Domain/Application负责普通规则/CRUD。

State保留必要ID/批次位置、manifest/预算引用、有限错误和pending decision。候选JSON写受授权的产物Repository，State引用其ID；ContextBuilder按scope获取少量内容，禁止塞完整业务知识树、原始历史、DB对象/秘密/大文档。

当前b3f2-batch-v1的批次快照和已验证providerledger不立即重构。新State协议采用新graph_version，仅新Run使用；旧waiting_user按原图版本恢复，历史checkpoint/journal/Attempt不覆写。批准/取消阶段不能重做生成；业务事务结果与checkpoint恢复显式核对。

## 后果与备选

可以按真实闭环增加有界流程，保留当前已验证链；需要有限旧图恢复入口和新增候选引用持久化。拒绝全生命周期大图、五空图、全量State替换、旧runtime重新迁入，以及通过批量改历史checkpoint完成升级。

## 验收

新图有明确输入/最大步骤/调用预算/终止条件；State体积受当前任务限额约束；旧waiting_user可批准/取消，provider新增请求0，重复决定不重复计划。新结构禁密钥和未授权上下文。
