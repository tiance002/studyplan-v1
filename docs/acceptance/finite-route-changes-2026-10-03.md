# 有限未来路线调整增量

用户现在新增能做什么：在规划页展开“调整未来路线”，移动尚未开始的阶段，或预览移除正式课程明确标成 optional 的未来阶段。先看前后差异，再明确确认新版本学习记录重新开始；刷新可恢复预览，确认后 PG 回读新路线，退出重登录仍可读取。已开始阶段及之前阶段保护位置，最终综合实践保留在末尾；旧路线、进度、总结、Prompt、成果及私人资料历史保留。

日期2026-10-03。实际本地代码 SHA **`736f0ba5dd202ffbd413e7894a6fb68b54451476`**，分支 `feat/n1-resource-discovery`，父 `c717e7aed1cb3f945d0ca4c9b234547a8992cfda`。固定点 `cf1537040bbf8c52469e00461723f70726f5a3b2` 祖先检查 PASS。新SHA未推送/核实为GitHub SHA。整体 **NOT_READY**，最终Goal active，未集成develop/master或接受milestone。

## Goal / 实际范围

继续[最终Goal](../implementation/STUDYPLAN_OCT6_FINAL_DELIVERY_GOAL_2026-10-03.md)第10节。第一切片实现 `reorder_future_stage` 与**阶段粒度**的 `remove_optional_topic`，不能宣称全部七种操作或阶段内任意单个topic移除已完成。正式Seed目前无明确optional阶段，界面会说明没有移除项；optional真实PG分支用隔离库合成Seed，不是正式课程发布。

- 100阶段上限，完整唯一顺序，拒绝无变化；必需闭包不丢失，前置顺序检查。不按标题或advanced猜optional。
- 固定原课程版本读取发布payload/digest；Seed inclusion枚举校验，缺省required。合并固定Seed前置与当前路线关联的知识边，已发布Seed不改。
- 活动边界来自当前计划位置Exposure/总结/Prompt/成果原文，保护最大活动序号之前的整个前缀。旧全局任务状态不把新版标完成；已有Exposure即使重置not_started仍算活动。
- 顺序影响未来指导时清除旧why/前次关系、对比、源码与基线声明，恢复unknown；实际任务验收保留，受保护前缀指导不改。
- 复用PlanDraft JSONB、同一PlanPublicationService、项目锁/版本CAS与链接重建，新增migration/依赖均0，不另建规划器。route metadata覆盖草案hash，通用保存/取消/发布入口禁止绕过；手动预览不创建AI Run。
- proposal ID由actor/project/idempotency key派生，异体冲突。确认、新版本、保留阶段私人选择copy lineage与决策回执同事务；确认前复查plan/version、学习、知识、任务、私人资料basis；故障整体回滚，确认/取消互斥。取消允许清理过期原预览。
- 前端缓存仅账号/项目隔离的proposal ID，GET恢复、显式重置确认、409保留、幂等键复用、退出迟到响应防护。共享DTO/OpenAPI/事务由root整合。
- 扩展mypy暴露既有DTO映射、list遮蔽、快照/冻结字典注解问题，已小范围修正；没有框架迁移或新许可证负担。

## Tests / Evidence

数量有重叠，不相加推算交付比例。规则/Fake、PG、真实公网分开。

| 验证 | 状态 | 实际结果与限制 |
|---|---|---|
| 新规则首次TDD | FAIL | 缺领域模块；随后实现并通过 |
| 最终定向规则 | PASS | 10通过，0.44s；含最后why/教程关系清除与实际任务验收保留 |
| 完整unit/contract | PASS | 658通过，38.16s；在最后why用例前，该差异由上行覆盖 |
| 既有2项skipped | NOT RUN | 不计PASS |
| 真实PG首轮 | FAIL | 4通过/1失败：首次内存时间与落库时间不同；改为保存后立即回读。随后Ruff删除fixture导入造成5 ERROR，显式重导入修复 |
| 有限规则+PG定向 | PASS | 16通过，18.23s；回读/幂等/历史/私人lineage/confirm-cancel竞争/入口防绕过/进度及私人basis/故障事务回滚 |
| 资源/实践/指导/有限PG回归 | PASS | 58通过，115.38s；1 deselected为独立浏览器。指导生成模型Fake，有限操作无模型 |
| 真实Chrome首轮 | FAIL | wrapper默认GBK读取UTF-8错误遮蔽诊断；之后定位隔离API未允许5178来源，登录被拒。仅验收container来源与显式UTF-8修复 |
| Chrome+真实HTTP/PG最终 | PASS | 1通过，12.93s；正常登录、保护边界、预览/刷新GET/显式确认/new plan回读/退出重登录/390px。只转发owned loopback API，无Fake业务响应 |
| Chrome Fake | PASS | locked/optional、预览/重置、恢复、409保留、幂等确认、账号/项目隔离、退出迟到响应；无PG/provider |
| Frontend unit/build | PASS | 11单元，TypeScript/Vite构建60模块；最后label仅澄清固定阶段原因 |
| Ruff/mypy | PASS | 最终受影响Ruff、4入口source及导入依赖mypy；首次6个类型错误FAIL，经定向修正后PASS |
| Diff/原文/秘密模式 | PASS | 暂存diff、25文件凭证模式；V2原文两份SHA256保持 |
| 真实收费模型/Tavily/GitHub | NOT RUN | 本批新增0，不用Fake代替真实服务 |

忽略证据 `var/oct6-guidance/`：`finite-route-unit-contract.xml`、`finite-route-pg-regression.xml`、`finite-route-browser-pg.xml`、`route-change-browser-pg.json`、`route-change-real-pg.png`。PG创建/迁移/写入/清理仅owned `studyplan_test_*` 库；临时Uvicorn停止，Vite5178保留，无旧Worker重派。只读复核未找到有证据P1；无关图谱边导致过期已缩小到当前路线依赖边；阶段级topic限制明确保留。

## 用量 / 风险 / 回滚 / 下一安全动作

追加账仍为模型 **23/50**、搜索 **4/1000**（旧unknown1），历史README2次；本批外部模型/搜索/内容/元数据均0。旧unknown/Acceptance不重派，账本不重置或改写。按最新用户决定GitHub DNS未配置，真正需要公开验证时才提示。

临时开发模型授权继续。原UI Sol/high代理有工具明确capacity错误，复用部分成果后新建Luna/high实施代理；另复用Luna/high只读审查。实际解析工具不返回，均 **NOT OBSERVABLE**。最多两业务写入者，root整合契约/事务；未改全局配置。快速服务模式偏好已记，但无可核实切换入口，不声称已切换。

原产品库未部署/写入，0023与仓库0024不变。其余有限操作、三正式Blueprint/免费正文章节审核、Worker/取消/失败/unknown/刷新恢复、完整闭环、真实provider/GitHub、备份恢复与用户接受仍未满足，整体NOT_READY。10月3日不批量扩内容，10月5日结束Feature Freeze。

普通 `git revert 736f0ba5dd202ffbd413e7894a6fb68b54451476` 可回滚代码，处理有依赖的后续代码；保留已产生路线/历史/账本，不降级0024。已有route预览须用支持该元数据的代码处理，不让旧通用入口绕过。下一动作推进 change_goal/add_topic/regenerate_future_plan 的有界草案生成与常态Worker恢复UX；已有Primary/Practice继续复用。缺RAG契约仅暂停支线，思想全文等待已发送问题的回复，不重复问。
