# S0：V1 规格收口验收记录

日期2026-10-01；本地审查基线 `ba7f5f50dc187dd99e75305e08648971440aa675`，业务基线仍为此前已推送 `3967168bd84fbbb312cca65ddcea6315dbf6100d`。本文件只记录S0文档交付，不声明M1–M4.5已完成。

## 交付

- [补充原文](../design-package/supplements/studyplan_requirements_design_supplement_2026-10-01.md)逐字保存，SHA256 `C98B4F5D06845B133B7F877B2D106EFFD57013085E6877626C0862DAD3274CFA`。
- [五类Gap](../reviews/2026-10-01-v1-gap-analysis.md)有来源、代码证据、处理决定、主里程碑和验收；全部15个补充章节有映射。
- [设计入口](../design-package/README.md)及PRODUCT_SCOPE/DOMAIN_MODEL/ARCHITECTURE/LEARNING_WORKFLOW/RAG_DESIGN/MEMORY_CONTEXT/MODEL_ROUTING/FRONTEND_INTERACTION/EVALUATION_ACCEPTANCE收口。
- [ADR0007–0009与索引](../adr/README.md)明确旧注册/固定三图决策取代范围；旧Accepted正文未修改。
- [实施路线](../design-package/IMPLEMENTATION_PLAN.md)保留B0–B6历史映射，定义M0–M4.5；AGENTS加入新权威入口、边界、验证和付费规则。
- [Acceptance09记录](b3f2/real-provider/2026-10-01-run09-result.md)保存已核对的20请求/1repair/待审批事实；批准/发布/学习闭环NOT RUN。

## 关键决定与下一切片

本地个人入口复用原actor/模型/Project scope；不删除认证表或历史迁移。PlanRevision承接PlanVersion；稳定knowledge_node_id需要逻辑身份与不可变内容映射，当前全量内容hash node_id尚不满足。Summary/Session补原版本/节点/来源；LangGraph保持有界且保护旧waiting_user；RAG/Memory/路由增量接入。

第一个业务Goal为M1.1本地入口安全装配；之后M1.2稳定身份，再M1.3最小调整/M2一节点学习闭环。M1.4 State收缩采用新Run协议，不重构或迁移历史Run。

## 检查结果

| 检查 | 状态与范围 |
|---|---|
| 原文与副本字节/hash | PASS |
| 文件变更范围仅AGENTS/docs | PASS |
| 文档diff whitespace | PASS |
| 全部变更文档本地链接 | PASS |
| 补充章节/五类Gap/八场景/五危险边界覆盖 | PASS |
| 既有journal/evidence哈希、旧ADR正文/业务源码 | PASS |
| 独立文档审核 | PASS，无阻塞或重要冲突；范围为本轮全部变更文档及关键代码证据 |
| 业务测试/大型suite | NOT RUN，文档Goal |
| 新真实模型验收 | NOT RUN，未授权 |

命令入口：`git diff --check`，repo venv运行一次性文档链接/章节/允许范围/hash检查。原始结果和任务账本保存在忽略的 `D:/studyplan/var/codex-goals/v1-s0-spec-freeze.json`。最终Git SHA由完成报告给出，不用尚未存在的远端SHA作证。

## 操作边界

本轮新增应用provider请求=0、新真实Run=0、数据库读写调用=0；历史Attempt/Run/journal/evidence不变；未操作.workbuddy/design-preview；未安装依赖、未运行模型命令、未创建tag/合并master。

P1实现缺口仍按所属阶段解决；P2延期未替负责人确认。只有完成M4.5真实完整闭环并由负责人接受后才能声明V1可交付。
