# ADR-0001：新版使用独立 Git 仓库与独立历史

- **状态**：Accepted（B0 冻结）
- **日期**：2026-09-27
- **决策者**：B0 Goal / SeniorDeveloper
- **关联**：`SOFTWARE_DESIGN.md` §0 §10、`IMPLEMENTATION_PLAN.md` §0

## 背景

旧工程位于 `E:\codex_workspace\study-plan`，其 Git 历史长达 2026-09-18 至 09-25，横跨 15 个本地分支（其中 10 个从未推送），并携带一套已废弃的业务假设（邀请码链路、自研 workflow runtime、旧 knowledge 索引引擎、旧 21 条迁移链）。新版 `D:\studyplan` 是 V1.1-LG 架构，编排层换为 LangGraph，业务域按六个限界上下文重划。

如果新版沿用旧 `.git`，会出现两个不可接受的问题：

1. **历史噪音**：新版的架构决策（三张小图、checkpoint 独立库、领域表为唯一事实源）会被淹没在 300+ 条与旧架构绑定的提交里，"为什么这样设计"无法从历史读出。
2. **误 revert 风险**：旧历史中存在被有意删除的东西（如邀请码链路 —— 见 commit `508a694` / `16c868d`）。一旦共用历史，`git revert` 或 `git checkout <old-sha> -- path` 会**无声地恢复已被产品否决的功能**。

## 决策

新版使用**独立 Git 仓库与独立历史**：

- `D:\studyplan` 自建 `.git`，初始分支 `master`，**从零开始**，不通过 `git remote add` 关联旧仓库，不做 `--allow-unrelated-histories` 合并。
- 不复制旧 `.git/`、不 `git clone` 旧仓库、不创建指向 `E:\codex_workspace\study-plan` 的软链或目录联接。
- 模块来源通过**文档化的溯源表**（`docs/migration/source-provenance.md`）表达，而不是通过 Git 祖先关系表达。
- 旧仓库 HEAD 作为**溯源引用**记录在文档中：`1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1`。
- 推送目标为**新建的独立远端仓库**，与 `tiance002/study-agent-platform` 无关联。

## 后果

**正面**

- 新历史可直接回答"V1.1 的每个架构决策在什么时候、因为什么被确定"。
- 邀请码等已否决能力**在物理上不可达**，不存在误 revert 的路径。
- 新仓库的权限、CI、分支保护可独立配置，不受旧仓库协作者与规则影响。

**负面 / 代价**

- 丢失旧仓库的行级 `git blame` 追溯。**缓解**：`source-provenance.md` 记录每个迁入文件的 SHA-256 + 旧 HEAD，需要时可回旧仓库按 hash 定位。本批次实际迁入 0 个文件，代价为零。
- 旧仓库 10 个未推送分支的内容在新仓库中不可见。**缓解**：这些分支内容在 `legacy-inventory.md` §3 已完整登记；旧仓库本身保持只读完整，不删除。

## 拒绝的备选方案

| 方案 | 拒绝理由 |
|---|---|
| 在旧 `.git` 上建新版分支 | 违反「旧版只读」约束；且会把新版架构决策混进旧历史 |
| `git clone` 旧仓库后改 origin | 同上，且带入 `main` 停在 09-21 的落后状态，易误导 |
| `--allow-unrelated-histories` 合并两条历史 | 保留误 revert 路径，正是本 ADR 要消除的风险 |
| submodule / subtree 引用旧仓库 | 会让 `D:\studyplan` 在**构建期**依赖 E 盘，直接违反「D 盘不依赖 E 盘环境」验收条款 |
