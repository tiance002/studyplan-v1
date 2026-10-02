# 受控主题追加与公开GitHub DNS验收

日期：2026-10-03。用户现在新增能做什么：在规划页勾选当前课程尚未覆盖的受控主题，自动补齐父/前置依赖及同阶段内容，生成差异草案，经明确确认发布新路线；刷新、重登录可以读回。已开始前缀、旧阶段与旧历史保留，新版不继承完成状态。当前正式Seed已覆盖全部主题，页面如实显示无可追加主题；可选模块的正式内容仍须后续Blueprint批次。原产品库未部署此增量，整体 **NOT_READY**。

代码本地SHA：`1a8b3f69820bdb3b763232a071b8c40bd1cee4c4`，分支`feat/n1-resource-discovery`。固定参考`cf1537040bbf8c52469e00461723f70726f5a3b2`祖先PASS；未推送/核实新远端SHA。本报告之后文档提交的SHA须另读实际HEAD。

## 实现与边界

- `domain/generated_plan_changes.py`：明确知识键、最多20项；闭包沿父/前置展开，迭代包含同阶段其它知识的前置。按受控`node_keys`/明确归属插入阶段，保留原相对顺序、保护前缀和最后综合实践；未知、已覆盖、歧义归属、循环或无法保护的插入拒绝。不按标题推断，不另建planner。
- `infrastructure/db/generated_plan_changes.py`、`plan_changes.py`：复用冻结提交、Worker、草案、项目锁/CAS/late fence及唯一publisher。保留当前阶段精确知识ID/content_version；阶段插入造成过时前次关系/基线时失效指导。主题标题冻结进草案哈希，页面显示可读标题。私人选取沿旧来源lineage复制，原正文不传模型。空`topic_keys`不改变旧幂等输入hash。
- DTO/OpenAPI/TS、`PlanChanges.tsx`：复用一个Run恢复和差异决定路径；不提供任意自由主题追加。按完整受控课程生成后过滤保留候选，目前尚非仅新增阶段费用优化。无新migration、依赖、框架或全局配置。
- opt-in live GitHub测试与账本transport：每个请求先独占追加reservation，再固定公网/TLS读取；无重试、redirect、代理环境或仓库执行。旧unknown/Acceptance不重派，未存response正文或密钥。

## Tests与证据

规则/契约与Fake模型、真实PG、真实外部、浏览器分别记录，数量重叠不相加。忽略证据目录`var/oct6-guidance/`。

| 验证 | 状态 | 证据范围 |
| --- | --- | --- |
| 较宽unit/contract | PASS | 705项；另2 skipped为NOT RUN，`add-topic-all-unit-contract.xml`，最终标题DTO前同域规则输入 |
| 最终定向规则/幂等/contract | PASS | 77项，`add-topic-final-unit-contract.xml` |
| 新增生成操作及旧生成回归，真实owned PG/HTTP/Worker，模型Fake | PASS | 7项，`add-topic-generated-regression-pg-final.xml`；追加/私人来源/历史、无效/跨项目/CSRF拒绝、学习变更后外发前fence、旧change_goal/regen/unknown |
| 最终标题快照PG及两个Chrome链路，模型Fake | PASS | 3项，`add-topic-labels-and-browser-final.xml`；普通登录、真实HTTP/PG/Worker、reload、差异、明确confirm、relogin、不重派；`add-topic-real-pg.png`已查看 |
| Frontend unit/build、主题与旧生成Fake Chrome | PASS | 11项前端规则；最终build、两个Fake Chrome PASS |
| Ruff、mypy、diff、凭据模式扫描、受保护原文hash | PASS | 4入口类型检查，15代码/测试文件凭据模式0匹配；V2原文hash未变 |
| 本机DNS/TLS、公开GitHub搜索 | PASS | DNS `20.205.243.168`；新编号01和02均HTTP200，第二次返回5候选，含`shareAI-lab/learn-claude-code` |
| 本次公开GitHub浏览器完整链 | FAIL | 01空结果；02因测试错误要求目标仓库排第一中断，目标实际在候选中。修正为显式选择目标候选，尚未再次执行 |
| 本次真实README/章节、私人映射刷新回读 | NOT RUN | 未进入inspection，新增文件读取0，不能以搜索200冒充完整链 |
| 本次收费模型/Tavily、原产品库迁移/写入、三正式Blueprint、最终全闭环与备份恢复/用户接受 | NOT RUN | 独立剩余门禁 |

已保留早期FAIL：缺主题入口、旧空字段幂等冲突、同伴前置缺失、新阶段过时指导、标题缺失的RED；浏览器先等待折叠预览导致timeout后修正；合成optional与普通课程误用同一不可变版本导致PG fixture ERROR后用独立版本/明确fixture选择修正。Ruff/mypy与Fake标题断言失败均已修复。只读review曾误将0005 downgrade的unique约束当作当前约束，核对upgrade后撤回该P1；未因此盲选历史节点或修改迁移。

## 用量、风险与下一动作

产品模型仍`23/50`，搜索累计`6/1000`，旧unknown1保留；本批新增2公开搜索、收费模型/Tavily/内容/metadata均0。首批新增公开搜索上限3已用完：旧unknown1+本次2；内容9/metadata6额外额度仍未使用，旧README读取2保留。`.git/v2-search-quota-20261001/request-0005/0006.json`及各result仅追加。临时API/Worker结束关闭、owned测试库清理，PG5432与自有Vite5178不变，原产品库未写入。

已向用户询问额外1次公开搜索以完成修正后的真实链，未把预选或沉默视作授权；不扩大首批额度、不重置账本、不重放旧请求。此支线等待时继续常态Worker取消、服务器侧运行查找/恢复及启动说明。现有unknown fail-closed与迟到结果防护继续保留，尚无queued/running单Run取消API或丢失localStorage后的服务端查找入口。

用户最新明确停止6Astra后，后续不再申请该模型。开发子任务请求沿Sol/medium、Luna/high，工具未提供实际解析，记录NOT OBSERVABLE；快速服务模式无可核实开关，未声称切换。最多2业务写者，共享契约/事务由主协调整合。

当前仅owned测试数据且已清理，可正常revert本代码SHA保留提交历史；如果日后已有add_topic草案或新版本，回退旧版前须保留新payload的读取兼容，不能删除历史、降级迁移或恢复旧Run。完整门禁及用户接受仍未满足，不no-ff/master/milestone，不推算交付百分比。
