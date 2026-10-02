# ADR-0015：学习编排语义与10月6日交付边界

日期：2026-10-03。依据：[最终交付 Goal](../implementation/STUDYPLAN_OCT6_FINAL_DELIVERY_GOAL_2026-10-03.md)。用户最新决定优先，既有阶段总结与自动阶段完成规则继续生效。

本轮复核实际 HEAD `3f31b182855c608bbc48fdf185204494eb4be09c`，分支 `feat/n1-resource-discovery`，固定参考点为祖先。复用上一批未提交 N1 资料发现实现，不切回 master 或固定点。迁移 head 0024，其中0024为尚未发布的 N1 资料预约增量；本次学习编排不新增迁移。

P0差异核查：DomainPack 阶段蓝图已有完整 JSON，生成有冻结清单与阶段结构/实践批次；但原 PlanStage 只保留标题、目标和顺序，投影会丢失学习目的、前次关系、对比问题、贯穿实践增量和源码建议。原工作区也没有相应显示。已有草案编辑、普通事务确认、持久 Worker 与阶段完成投影直接复用。

每阶段增加可选 `learning_guidance`：why_now、previous_relation、learning_focus、comparison_focus、practice_delta（baseline/increment/preserved/validation/reuse）、source_slice、exposure_relation、knowledge_keys。关系只接受 review/compare/deepen/version_context/unknown；这不是掌握状态或分数。

受控 Seed 预置的关系、知识键和源码建议成为生成条件。代码在冻结与合并时校验、引用原值；模型不能将自己生成的“已学过/已审核”声明提升为事实。旧模板仅展示基于已有 objective/practice blueprint 的有界说明，明确没有已审核的教程关系。临时搜索候选不自动写入公共关系。源码建议只接受公开 GitHub 仓库入口，展示 ref 与核验状态，不读取或执行外部代码。

持久化复用 `plan_drafts.payload.stages[].learning_guidance` 和 `plan_revisions.structure.stages[].learning_guidance`。规范化阶段表仍是既有结构字段的唯一读回依据；仅新增指导元数据按 stable_key 从该计划版本的 JSONB 读回。草案哈希和版本指纹覆盖指导；旧数据无字段时不改变原哈希。重建版本与旧客户端编辑保留原指导，不允许编辑请求伪造来源/已学事实。用户明确改目标或主线后必须在新草案重新审核相关指导，不能继承旧完成状态。

Tool Calling fixture 的起点仅属于明确给定的合成输入；它不是所有用户的默认经历，也不是公共发布 Seed。当前源码文件未核对，路径留空且状态 suggested，正式内容仍须免费正文、章节顺序与来源审核。P1–P4真实外部模型验证与 Fake/PG/浏览器分开记录。

受控模板可以在不同阶段引用同一个精确知识 stable_key，但必须明确声明 review/compare/deepen/version_context 关系及本次知识键。合并只复用规范知识节点，保留不同单元及独立 Exposure；未声明、同阶段或临时搜索产生的重复继续拒绝。真实PG已证明两次学习位置复用一个知识身份，同时学习记录互不继承。Seed导入先校验指导结构与知识键，不等到模型调用后才发现错误。

Practice Change 根据新草案的实际任务目标与验收要求重建受影响阶段的实践指导，清除过时对比和源码建议；Primary替换将旧教程关系恢复为 unknown，要求重新核对。两者均创建新版本，旧指导和旧历史保留，不继承旧 accepted 状态。

10月3日不批量扩内容；后续三个正式 Blueprint、有限操作重规划、常态 Worker 恢复与最终E2E继续属于交付门禁。GitHub OAuth/私有仓库列为非核心增强；独立 RAG 到10月4日中午按新 Goal 判定，缺契约不阻塞其它工作，不猜接口。整体保持 NOT_READY。

回滚采用普通 revert 新增代码，保留既有数据库历史及账本。指导元数据在原 JSONB 中可由新代码再次读回，无需破坏性降级。不得重写已发布 Seed、迁移或旧 unknown 记录。当前未提供的《规划算法思想校正版 v1.0》全文已请求路径；已按最终 Goal 中明确列出的校正规则实施，收到全文后只审计新增差异。
