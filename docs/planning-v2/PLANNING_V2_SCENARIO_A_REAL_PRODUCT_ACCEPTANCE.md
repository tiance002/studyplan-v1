# Scenario A 真实课程与产品闭环验收

任务：`PLANNING_V2_SCENARIO_A_REAL_PRODUCT_ACCEPTANCE_V1`。

## 基线、授权与执行状态

Start HEAD：`2706fd531b7d4caa25127c588c0e2c97b1a1fd86`；分支 `feat/n1-resource-discovery`，与本轮参考一致。开始时 tracked tree clean；既有 `.workbuddy/` 和 `design-preview/` 未操作。

Owner 单独确认最多 9 次产品模型（Goal 1、Capability 1、Reader 6、Curriculum 1）、6 次搜索、6 次正文操作/12 次 HTTP、官方价格与余额合计 2 次，并接受没有严格人民币数学现金上限的残余风险。随后批准先实施最小 owned 门禁、离线验证，再执行本批。无充值、重试、repair、换模型、扩额、正式数据库写入或公开生成授权。

当前阶段为门禁离线收口；真实外部验收 **NOT RUN**。最终执行结果将在本报告追加，不把离线材料或历史184/187替代本批真实结果。

## 最小受控门禁

新 owned assembly 显式选择 `scenario-a-review-v1`，冻结 `planning-v2-product-v2`。旧 manifest、旧 Run 和无标记装配继续原行为；未改架构业务语义、Policy、Prompt、Schema、历史快照或 migration。

- 四模型 purpose 独立上限 1/1/6/1；搜索/正文各6；其他 purpose 在 invoke 前拒绝。
- Provider 实际基础输出4096、Reader1024；manifest 相同冻结上限，总最坏输出18432。
- 新 owned `ResearchBudget`：search6、candidate8、body393216bytes、Reader6、total27、internal cost186000。27=9模型+6搜索+12正文HTTP；internal cost不是人民币。
- Goal、Capability、Curriculum 真实 checkpoint 后，受当前 fence 保护保存绑定审查事件，Run进入 `waiting_user`、`result_ref=NULL`，原 Job 完成并撤销租约。
- 独立审核决定绑定 actor/project、同 Run/root、manifest、stage、checkpoint hash、Run version、审核证据hash和幂等key。批准原 Job 续接、保留 attempts 与累计预算；拒绝、unknown、过期/篡改来源不续发。
- 三次审核加最终持久化最多4次 bounded claim；不通过异常或崩溃模拟暂停，不创建公共审核API或通用暂停平台。

源码：`plan_service.py`、`v2_runtime.py`、`v2_planning_runtime.py`、`runtime_factory.py`、`v2_attempts.py`，新增 `v2_owned_reviews.py`；定向 unit/owned PG 两个测试文件。

## 离线验证与独立审查

| 验证 | 状态 | 证据/范围 |
|---|---|---|
| 新门禁及相邻定向 unit | PASS | 46项，`var/planning-v2-scenario-a-20261010/owned-gate/final-unit.log`，exit0 |
| 新 owned PG / 真实 PostgresSaver | PASS | 8项，`final-owned-pg.log`，exit0；三暂停、同Run恢复、CAS/幂等、旧fence/unknown/篡改拒绝、全最坏累计和逐purpose超额0invoke |
| Wire harness 反例 | PASS | 9项 MockTransport；可信usage、缺usage、截断、超大输入、purpose耗尽，以及Reader正文/usage额外值/usage错误类型/finishReason回显 |
| 相邻旧 runtime PG | PASS | 先6PASS/1FAIL（旧V1 fixture没有显式选择legacy）；仅为fixture补`product_semantics=None`后原失败单项PASS，保留原始失败日志 |
| Ruff / diff | PASS | 本轮相关文件；不重跑283项旧回归 |
| 真实模型、搜索、Reader、正文、官方元数据 | NOT RUN | 门禁完成后才按既有授权执行 |

独立审查发现 Reader 原始响应可能在拒绝前回显并持久化教材正文；usage和finishReason也有相同元数据旁路。采集已修为只保留 Reader 原始响应的 hash/status/bytes；仅严格校验通过的有界事实可保留，拒绝时不保存 payload。usage仅投影可信三个计量整数，finishReason仅枚举/None，其他值仅hash。四个哨兵反例证明这些回显不出现在任何保留文件。Reader原始响应不因验收日志要求而越过正文保护。

独审还要求门禁源码本地提交后再冻结执行文件，防止新未tracked模块未纳入hash保护。执行freeze拒绝dirty tracked tree，并确认新模块已tracked。

开发审查请求 Sol6.1 xhigh，实际模型解析 **NOT OBSERVABLE**。独立 critical 审查 **PASS**：独立以内存方式再运行9项Mock矩阵，读取8项owned PG/46项unit证据并核对源码顺序；没有剩余confirmed blocker。旧runtime相关7项最终PASS，原fixture失败日志保留。审批接口返回原Run身份，不改变历史事实。

## 后续真实执行与报告范围

沿用原 Scenario A GoalSpec；新 acceptance、Run/Job/root 和 append-only 请求身份。独立语义审查 PASS 后才能继续各阶段。实际消息序列化检查、严格模型/finishReason/usage核对，任何 unknown、截断、不可托信usage、Validator或关键语义失败即停止。费用只按实时官方峰值未命中价格估算，不冒充实际扣款或数学现金硬上限。

原始证据目录：`var/planning-v2-scenario-a-product-acceptance-20261010/`。不保存凭据或认证头；教材正文保持瞬态。历史账本unknown177/183与184–187原证据受hash保护。

仅真实 Curriculum 完整且双层审核通过才执行 Compiler/owned PG/Draft/确认/Revision/React。否则这些产品闭环项目记录 NOT RUN。任何结果都不开放公开 `/plans/generate`，不 push、merge、deploy。
