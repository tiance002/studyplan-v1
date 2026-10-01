# G2第一批：真实搜索与单元私有资料

2026-10-01，整体NOT_READY。用户现在可在阶段工作区指定学习单元，显式搜索资料、选用候选或手动添加文档/GitHub网址；刷新后仍能读取选择，移除只结束当前选择并保留历史。结果显示未核验，选用不代表完成学习、内容质量审核或GitHub账号连接。

## Goal与边界

Goal：Tavily→未核验候选→明确选择→指定plan/stage/unit私有快照→PG及浏览器回读。Allowed changes为新资源Port/服务/适配器、增量0013、有限API/DTO及现有工作区组件；复用资源记录和计划单元，不重建目录。Constraints：服务端scope/RLS、当前版本锁、原子写入、无重试、无候选页面抓取/外部仓库执行；秘密只在本机。Non-goals：公共Seed升级、已确认主线替换、完整Exposure/进度/偏好/六角色、GitHub OAuth、真实RAG。这些仍在G2范围，不宣称本批完成整个切片。

产品预算0013按数据库全局累计（最高1000），短事务预约后才HTTP；同键同体回读，异体409，0预算不派发。未知/异常持久reconciliation_required，不泄露上游异常；同key不重试。验收跨库另由.git累计journal约束，承接G1的1次搜索而非从0开始。

## Tests与Evidence

| 命令或检查 | 状态 | 结果/范围 |
|---|---|---|
| pytest backend/tests/unit/test_tavily_resource_index.py backend/tests/unit/test_domain_invariants.py --tb=short | PASS | 80离线，含50adapter；不代表真实服务 |
| pytest backend/tests/contract backend/tests/unit/test_tavily_resource_index.py backend/tests/integration/test_learning_resources_pg.py --tb=short | PASS | 89，exit0；50adapter、31契约、8真实PG |
| 新0预算/非法Unicode/异常未知/手动公开DNS定向复查 | PASS | 最终4，5 deselected，exit0；复用未失效的89项证据，不合并为虚构一次全量结果 |
| frontend npm test、npm run build | PASS | 4单元及实际TypeScript/Vite构建 |
| node tests/resource-picker.browser.cjs，STUDYPLAN_URL=127.0.0.1:5174 | PASS | 明确mock；GET只读恢复/404显式原键提交、切单元迟到结果隔离、输入保全 |
| V2_CONFIRM_SEARCH_RUN=1 node tests/learning-resources-real.browser.cjs | PASS | Chrome+真实Tavily+HTTP+隔离PG，5候选/选取/手动/刷新/原查询读取 |
| backend Ruff、git diff --check | PASS | exit0 |
| Exposure、偏好、角色及RAG完整G2验收 | NOT RUN | 尚未实现或外部契约缺；不删除目标 |

所有Python命令使用D:\studyplan\.venv\Scripts\python.exe；普通PG测试在独立studyplan_test_*并自动清理，无外部调用。真实验收沿用本轮自己的真实模型计划和隔离账号，业务库studyplan_test_v2g1real_2f6ac462新增0013；checkpoint库不变，不重生成或批准任何新/旧Draft。原用户业务库/8000服务不动。

审查发现当前资源写与发布未共享版本锁：先增加PG竞争回归得到FAIL，复用现有plan-decision锁并在等待后重读approved；定向PG PASS。第一次HTTP契约测试暴露真实unit_id比64长，改按opaque ID允许512并同步契约。首次真实浏览器命令FAIL为本机验收journal以GBK读取UTF-8，在HTTP派发前失败（实际搜索仍1）；修复验收脚本，保留原预约不重派，以显式新请求执行本次成功。未修改/删除历史收费记录。

新AcceptanceId v2-g2-20261001-01。第二次实际Tavily request_id 6cbd7349-21f3-43a4-91a5-aaf32207d55c，HTTP200、credits1、unknown=false。累计搜索2/1000、模型20/50；读取原查询、刷新、手动URL均未产生搜索/模型请求。截图与JSON在var/v2-g2/learning-resources-real.*；原始计量.git/v2-search-quota-20261001/request-0002.json及result-0002.json。测试账号秘密不得打印/提交。

## Rollback与下一批

普通revert保留0013和历史记录；存在选择/搜索/计数时downgrade拒绝数据丢失。撤回单元资料只写removed_at，历史snapshot不读公共目录最新内容。普通用户体验接受NOT RUN。

下一批仍需Exposure独立出现位置/进度/跳过/返回/历史、局部偏好继承、六种角色、受控资源替换、GitHub授权连接及RAG薄适配。代码提交与远端身份由[唯一检查点](../implementation/progress.md)维护。
