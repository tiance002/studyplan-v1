# ADR-0007：V1 本地个人入口与既有身份安全衔接

- 状态：Accepted（用户2026-10-01补充规格）；实现待M1.1。
- 取代：ADR-0006 将开放注册/登录及特定口令政策作为V1交付要求的部分。原文保留为历史；旧认证仍在当前代码运行，S0未改码。
- 关联：[PRODUCT_SCOPE](../design-package/PRODUCT_SCOPE.md)、[Gap E1/D1](../reviews/2026-10-01-v1-gap-analysis.md)。

## 决策

V1正式入口为个人本地学习空间，不要求注册登录。服务端使用明确配置的既有本地actor，复用 STUDYPLAN_LOCAL_ACTOR_ID 等配置能力；配置存在不等于目前DB路径已无登录，须补组合根/Session adapter/UI装配。

目标本地模式仅loopback提供服务，验证允许的Host/Origin、跨站写保护；不得信任请求体的actor/project归属。worker同一actor allowlist/scope，DB/FK/RLS/模型凭据归属不关闭。actor缺失/多候选未绑定/非本地暴露拒绝，不能自动选首账号或创建新actor使历史数据失联。

切换前核对原Project/模型/Run归属，绑定原actor，保持本仓库历史数据。认证表/迁移/ledger暂保留；后续收缩入口按明确小切片完成，不建立两套长期产品认证。不支持旧E盘数据/API。

## 后果与备选

复用现有actor与安全机制，减少账号产品成本；过渡需要保护已有认证关联和waiting_user。拒绝删除auth表/关闭RLS/客户端自报身份/自动重建用户；这些会破坏数据归属或暴露模型配置。未来云端身份另立ADR，不提前建设SaaS/RBAC。

## 验收

原Project/个人模型/Run可访问；错误actor或跨Project拒绝；缺绑定、伪造客户端身份、非loopback及错误Origin拒绝；当前waiting_user批准/取消不产生provider请求。本地产品入口接通前，旧浏览器登录仍是运行事实，不能声称已移除。
