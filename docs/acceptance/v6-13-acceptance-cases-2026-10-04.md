# v6.13 定向27项与v6.12原31项续接

状态仅 PASS / FAIL / NOT RUN；所需层未完成不能由另一层替代。

## v6.13 定向案例

| ID | 要求 | 状态 | 实际证据与缺层（均位于var/v613） |
|---|---|---|---|
| C01 | 原pre-save仅改顶层canonical/teaching rubric | PASS | projection-expanded.xml; original pre-save compiled InMemorySaver attack, save0/dispatch0 |
| C02 | 相同反例使用真Postgres checkpoint与owned业务PG | PASS | pg/pg-projection-canonical_rubric.json; real PostgresSaver+fresh independentSQL, all business counts0 |
| C03 | 直接应用保存入口，不经过executor | PASS | test_v613_contract_pg direct _persist_draft malicious fixtures; reject before materialize |
| C04 | normalized batch与顶层同时替换，或伪造原始presentation | PASS | pg/pg-projection-dual_presentation.json; projection-expanded foreign Run/raw+normalized+final attacks |
| C05 | 同数量但资源refs/roles、guidance、unit links或task acceptance变更 | PASS | projection-expanded.xml exact identities/order/links/rubric/practice acceptance/resources/guidance/extensions; actualPG resource-role reject |
| C06 | 没有篡改的正常生成和post-merge恢复 | PASS | pg/pg-projection-valid.json; pg/pg-known-repair-replay.json exact pending knownreceipt SQL replayHTTP0 |
| C07 | 合法编辑、资源替换、任务变更、未来路线保留前缀 | PASS | pg/pg-edit-cancel.json + compatibility-pg.xml resource/task formal revisions and generated future prefix/history cases |
| C08 | 取消/租约过期/并发重复确认 | PASS | compatibility-pg.xml cancellation/live claim/replaced lease/late outcome cases + compatibility-route-pg.xml concurrency/rollback; fixture recheck1PASS |
| C09 | 删外层structure marker与hash，残留focus/batch marker | PASS | projection-expanded.xml incomplete direct generate/repair marker variants |
| C10 | 删全部checkpoint新marker/hash，Run冻结记录仍为新合同 | PASS | projection-expanded.xml all markers/hash removed vs independent original manifest |
| C11 | unknown/null/空值/outer-batch冲突或其他run/stage合同 | PASS | projection-expanded.xml null/unknown/perbatch mismatch; unit/contract final |
| C12 | 真正legacy与短outline+旧structure历史 | PASS | pg/pg-legacy-full.json and pg/pg-legacy-outline.json; no marker retrofit; legacy payload/fingerprint targeted existing tests |
| C13 | 混合reviewed/search_only及无固定目录旧Python | PASS | pg/pg-python.json pg/pg-search-only.json; unit/contract reviewed/search mixed eligibility |
| C14 | W6原句不默认学K8s＋合法ref要求Must deploy a Kubernetes cluster | PASS | focus-repair-final-v2.xml W6 negative text is not practice permission EN/ZH |
| C15 | 同主题中文强制、禁止性解释、comparison-only、其他未选focus提及 | PASS | focus-repair-final-v2.xml selected comparison/unselected ref/negative explanation EN/ZH |
| C16 | Cloud合法Kubernetes实践正例 | PASS | focus-repair-final-v2.xml lawful CloudS5 practice, explicit GoalSpec exclusion and unrelated constraint control |
| C17 | node/ref合法但目标内新增费用或外部副作用义务 | PASS | focus-repair-final-v2.xml payment/new mandatory expansion; canonical task guards remain |
| C18 | A2原11058字符/六objective1807/额外acceptance失败对象 | PASS | focus-repair-final-v2.xml original11058 object reaches MockTransport with complete raw+errors |
| C19 | 转义/Unicode/接近上界的完整失败对象与错误列表 | PASS | focus-repair-final-v2.xml JSON escaped Unicode/ASCII aggregate boundary sides |
| C20 | 真正超大失败对象或本地预算配置不成立 | PASS | focus-repair-final-v2.xml oversized guard before Fake/HTTP/PgAttempt connect, repair_count0 |
| C21 | repair返回partial/仍非法/发生unknown | PASS | focus-repair-final-v2.xml partial/two repairs/unknown; pg/pg-known-repair-replay.json SQL retained result recovery HTTP0 |
| C22 | Agent+RAG18阶段真实owned Plan消费 | FAIL | pg/pg-rag.json PASS, actual Edge A2/core/specialty PASS; GR4 duplicate pending cards FAIL; refresh/relogin NOT RUN |
| C23 | GR替代候选/长guidance/两类项目Prompt | FAIL | pg/pg-long.json PASS; actual GRcard FAIL, whole_core Prompt PASS, targeted mature/longguidance Edge NOT RUN |
| C24 | 窄MCP、已有Node服务代表 | NOT RUN | pg/pg-mcp.json and pg/pg-node.json PASS; actual Edge NOT RUN after STOP |
| C25 | Browser/Coding/Voice/旅行组合/AI已有项目及旧版本代表 | NOT RUN | Browser/Coding/travel/Voice/AI/Python/search-only current owned PG PASS; historical owned v68/v610 live PG consumption NOT RUN; protected hashes PASS |
| C26 | 真实代表前的manifest实际预算与账本 | NOT RUN | Prepared free_preflight.py only; actual binding/DNS/TLS/wire budget gate NOT RUN after STOP |
| C27 | 唯一全新Agent+RAG完整真实代表 | NOT RUN | No new paid Acceptance/Run; real provider requests0, existing45/100 unchanged |

## v6.12 31项原要求补证

原文矩阵保留，不覆盖历史状态。下表为本轮增量，具体要求仍由原矩阵决定。

| ID | 状态 | 本轮证据及保留边界 |
|---|---|---|
| B01 | PASS | ActualHEAD unchanged, existing candidate reused; noreset |
| B02 | PASS | Protected v610 raw parsedfixtures+v612exports unchanged |
| U01 | PASS | A2three visible actual owned Plan units/onecanonical/onetask Edge PASS |
| U02 | PASS | Four-field unit rejects nodes/relations/canonical injection |
| U03 | PASS | Foreign keys/focus/stage rejected; final batch/top/rawcompare |
| U04 | PASS | F2selected focus plus explicit negativeGoalSpec; EN/ZH covered; not general semantic proof |
| U05 | PASS | Three historical rawfixtures hashunchanged; oldcontract failure retained |
| U06 | PASS | F3complete repair/object aggregate/zero dispatch and count PASS |
| U07 | PASS | F4allmarkers/partial/null/unknown rejected; genuinelegacy PG no retrofit |
| U08 | PASS | PublishedPython2/search-only new actualAPI/ownedPG PASS |
| U09 | PASS | F1finalrubricguard realcheckpoint/application; actualA2pagevisible PASS |
| U10 | PASS | Local wire+fullrepair MockTransport PASS; capsunchanged |
| R01 | NOT RUN | SystemAgent9stages PG PASS; this actualEdge scenario NOT RUN |
| R02 | FAIL | RAG18stages PG+initial actualEdge mainline PASS; GR consumer FAIL; REAL NOT RUN |
| R03 | NOT RUN | Tool startingpoint twoinputs UNIT; narrowMCP4 PG PASS; actualEdge NOT RUN |
| R04 | PASS | Existing byte-unchanged course/unit evidence reused |
| R05 | PASS | Current Browser route persisted/confirmed/readback PG PASS |
| R06 | PASS | Current Coding route persisted/confirmed/readback PG PASS; TS independentreviewed course gap retained |
| R07 | PASS | Current travelWorkflow/Browser/RAG route persisted PG PASS |
| R08 | PASS | Existing explicitrecipeexclusion evidence reused with byte-identical candidate |
| R09 | PASS | Voice missingreviewedrecipe honest publiccore PG PASS |
| R10 | PASS | AI4 commerce owncarrier PG PASS |
| R11 | NOT RUN | Node11stage ownAPI continuity PG PASS; actualEdge NOT RUN |
| P01 | FAIL | Synthetic7007 orderedlongguidance PG PASS; actualRAG alternatives4duplicate cards FAIL; long actualEdge NOT RUN |
| P02 | NOT RUN | whole_core actual clipboard PASS; targeted mature Prompt actualEdge NOT RUN after STOP |
| P03 | PASS | Existing source/exposurecontext bounded evidence retained |
| V01 | NOT RUN | Oldhistories/currentpublishhash PASS, genuinelegacy PG PASS; originalv68/v610 live ownedPG consumption NOT RUN |
| V02 | PASS | RAG20units/16canonical/18tasks; A2three no extra requiredtask; taskacceptance exact PG |
| C01 | PASS | Fakeactual manifest37normal+2repair=39/output241664; hypothetical45+39=84/100; actualbinding freepreflight NOT RUN |
| C02 | NOT RUN | New structural STOP before realAcceptance/Run/provider |
| C03 | NOT RUN | Offline/PG unknown/failed guards PASS; current REAL anomaly gate NOT RUN |
