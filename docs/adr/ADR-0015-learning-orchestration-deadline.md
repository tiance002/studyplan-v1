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

目标解析首版是用户显式补充，不用收费模型猜画像。可选GoalSpec记录 target/scope/desired_depth/starting_point/outcome_purpose/constraints，未填写沿用旧goal请求。API和领域分别验证长度、数量及枚举；起点明确属于自述，不写掌握状态。经规范化值进入提交事件、带哈希manifest、各模型批次、草案payload和已确认版本structure，哈希保护该快照；资源/实践新版本沿用，恢复不从当前表单或新Seed重解析。

required module closure从受控Seed的required roots沿parent/prerequisite递归展开，稳定排序、去重并限制最多200个受控模块，unknown/cycle在派发前拒绝；未reachable的optional模块不因此变成必修。GoalSpec.scope目前只作模型条件，不能宣称已经实现任意主题裁剪。用途叠加仅给收尾实践增加少量可检查输出；最终指导与实际任务验收同步，实践更改时保留当前用途要求。阅读/实践前置先用有界指导字符串，空新字段不改变旧哈希，不另建图或迁移。

10月3日不批量扩内容；后续三个正式 Blueprint、有限操作重规划、常态 Worker 恢复与最终E2E继续属于交付门禁。GitHub OAuth/私有仓库列为非核心增强；独立 RAG 到10月4日中午按新 Goal 判定，缺契约不阻塞其它工作，不猜接口。整体保持 NOT_READY。

回滚采用普通 revert 新增代码，保留既有数据库历史及账本。指导元数据在原 JSONB 中可由新代码再次读回，无需破坏性降级。不得重写已发布 Seed、迁移或旧 unknown 记录。当前未提供的《规划算法思想校正版 v1.0》全文已请求路径；已按最终 Goal 中明确列出的校正规则实施，收到全文后只审计新增差异。

有限重规划第一增量支持调整未来阶段顺序、移除受控Seed明确optional的未来阶段。固定原课程版本的 inclusion 缺省required，不能从advanced/标题猜测；正式Seed没有optional时说明无移除项。学习边界按当前计划位置的真实原文/Exposure活动保护前缀；最终综合实践保留在最后，以保持用途验收位置。必要闭包和前置顺序由代码检查。当前remove_optional_topic是阶段粒度，不能宣称任意单个知识topic移除。

手动变更复用现有PlanDraft payload和唯一publisher。route_change元数据进入草案hash，专用入口负责确认，通用草案写入防绕过；决策回执存payload的独立生命周期字段，不改变原预览内容hash。确认、新版本、私人选择copy lineage、回执在同一项目锁/CAS事务，重新核对学习/任务/知识/私人basis；不派发模型/创建伪Run。新版不继承旧完成状态，历史留在旧版本。其余有限操作及最终门禁继续实施，详见[有限调整证据](../acceptance/finite-route-changes-2026-10-03.md)。
