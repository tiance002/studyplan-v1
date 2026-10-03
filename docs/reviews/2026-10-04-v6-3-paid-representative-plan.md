# RC-D2 收费代表路径计划：STOP，当前执行0次

本轮不调用真实收费模型。当前实际部署候选为 openai_compatible / api.deepseek.com / deepseek-flash； `.env`密钥SET，未输出、未用于任何HTTP请求。产品私人模型配置不借用，不解密其密钥发往外部。

## 免费结果与相关服务

- 真实产品copy恢复、PG catalog选择、manifest/预算计算均为本机离线：PASS，无provider HTTP。
- GitHub public教程搜索/README章节能力保留；本轮不需要额外公开请求，不消费或重置旧额度，真实服务本轮 NOT RUN。
- RAG仅免费本机health/OpenAPI GET16次尝试；实例选择及纯retrieval授权/citation/error契约未就绪，不加入模型代表调用。
- provider health/model list本轮NOT RUN；本机binding/config检查发现cap冲突，并非已完成真实provider验证。

## 推荐单一代表：Agent common core → 新草案

合成账号候选名 `rc_paid_agent_20261004`，在批准收费验证时另建全新owned业务库和独立checkpoint库；不是产品库或真实数据恢复副本。纯合成目标：“零基础系统学Agent，先做一个最小应用”，不加入用户真实项目、资料、旧Summary/Prompt/Outcome/Run。使用新的AcceptanceId/Run与追加账本；不复用旧unknown/Acceptance，也不自动批准草案。

当前Agent5私有裁剪为6阶段。冻结manifest计算：

| 项 | 上限 |
|---|---:|
| outline | 1请求，4096 output tokens |
| structure | 6请求，每次8192 |
| practice | 6请求，每次4096 |
| local repair | 最多2请求，每次8192；不是未知外部请求重试 |
| 正常无修复请求 | 13 |
| 整条Run最大请求 | 15 |
| output总预算 | 94208 tokens |

只有1个新Run；请求上限包含13正常批次和最多2本地内容修复。不能把“1个Run”写成“1次收费请求”。保留当前模型23/50，本代表最坏15次后38/50，尚余12；实际依append账本扣减，失败/unknown也计入，不保证使用满上限。美元费用本轮不估造，需按届时provider实际价格/输入使用量核对。

配置门禁：当前 `.env` deployment cap8000低于structure/repair8192，FAIL。候选总cap8192离线PASS；staging/代表进程仅用经批准候选设置，不能先跑再改预算。输入仅受审公开Seed与合成Goal；调用前重新检查冻结manifest输入、endpoint授权、token/request cap、key存在、独立账本、无未知重派及synthetic scope。

预期验证：真实endpoint/模型JSON协议与长输出能力；受审核章节/资源/扩展在真实输出后确定性保留；成功持久草案终态succeeded+none；真实截断/空响应/已知失败与unknown按现有规则处理，原文/预算不丢；刷新/重登录只GET，不再发收费请求。

Fake/历史不能替代：Fake不验证当前endpoint、真实返回格式/输出长度；旧真实回执不覆盖Agent5新manifest。失败即保留回执，不能为求绿连续派发新Run。

AI2和Cloud2仅作为后备离线计算，分别7/9阶段，最大17/21请求，output106496/131072；**不包含在推荐15请求授权请求中**。不同时运行三代表。

STOP：等待用户明确批准这一有界代表验证；当前真实收费执行0。私人正文、账号密码、产品模型密钥、加密数据及旧账本均不外发。后续批准收费不自动批准原库升级、正式入口切换或RAG修改。
