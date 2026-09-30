# Git Maintenance Audit — Before Cleanup

Captured: 2026-09-30 (Asia/Shanghai), before fetch or branch changes.
Repository: D:\studyplan

## Initial repository state

Current branch: codex/b3-f1
HEAD: 1683cbf2a1daa939c730777c1e029557b3384db7

Origin URL:
- Fetch: https://github.com/tiance002/studyplan-v1.git
- Push: https://github.com/tiance002/studyplan-v1.git

No root or nested AGENTS.md was found by rg --files -g AGENTS.md.

## git status --short

?? .workbuddy/
?? design-preview/

Tracked working-tree changes: none (git diff --stat was empty).
Staged changes: none (git diff --cached --stat was empty).

Untracked files from git status --short --untracked-files=all:
- .workbuddy/memory/2026-09-29.md
- design-preview/design-comparison.md
- design-preview/design-notes.md
- design-preview/scheme-a.html
- design-preview/scheme-b.html
- design-preview/screenshots/01-dashboard.png
- design-preview/screenshots/02-stage-workspace.png
- design-preview/screenshots/03-conversations.png
- design-preview/screenshots/04-learning-summary.png
- design-preview/screenshots/05-practice-detail.png
- design-preview/screenshots/a-dashboard.png
- design-preview/screenshots/a-workspace.png
- design-preview/screenshots/b-dashboard.png
- design-preview/screenshots/b-workspace.png
- design-preview/shot-v3.cjs
- design-preview/shot.cjs
- design-preview/studyplan-v2.html

These untracked files have not been deleted or modified.

## git branch -vv

* codex/b3-f1 1683cbf [origin/codex/b3-f1: ahead 4] docs(b3-f2): align Task 7 regression evidence with the final run
  master      f30d194 [origin/master: ahead 8, behind 3] feat(b3): add encrypted personal OpenAI-compatible model settings

## git branch -a

* codex/b3-f1
  master
  remotes/origin/HEAD -> origin/master
  remotes/origin/codex/b3-f1
  remotes/origin/master

## git remote -v

origin https://github.com/tiance002/studyplan-v1.git (fetch)
origin https://github.com/tiance002/studyplan-v1.git (push)

## git log --graph --decorate --oneline --all -40

* 1683cbf (HEAD -> codex/b3-f1) docs(b3-f2): align Task 7 regression evidence with the final run
* 4107fa3 feat(b3-f2): independent batched Fake E2E and real-graph progress fix
* 32d837e feat(b3-f2): per-stage generation progress on the planning page
* 572b068 feat(b3-f2): single batched protocol, frozen submission and RunProgress
* 2bd8445 (origin/codex/b3-f1) feat: resume batched runs by graph version and finish real legacy checkpoints
* 47cc67f feat: add batched planning protocol with frozen budget and bounded repair
* 38d042e feat: enqueue planning runs and add a fenced local worker
* 7b7fbc7 feat: add per-stage model output budgets and diagnostics
* c292cca docs: incorporate staged planning review and implementation plan
* 39e79ad docs: diagnose truncation and design staged planning generation
* ce7a749 fix(provider): control DeepSeek planning mode and retain failed usage
* e6218c2 test(b3-f2): verify full route and capture frontend acceptance
* ce81eaa feat(b3-f2): add domain-aware routes and chapter-linked workspace
*   6a187fc merge: integrate master B2-V history without losing B3 fixes
|\
| * a9c469e (origin/master, origin/HEAD) docs(b2v): 报告补充远端落地 SHA 与 tree 等价说明
| * 668f3bf docs(b2v): B2-V 验收报告（§一–§八，378 测试通过）
| * 932c434 feat(b2v): 发布边界修复 + 第一条业务垂直切片（§二–§七）
* | 76643cf fix(auth): clarify registration flow and errors
* | 5e032b5 feat(b3-f1): ship browser auth and V6.3 learning workspace closure
* | f30d194 (master) feat(b3): add encrypted personal OpenAI-compatible model settings
* | 5fbd4af docs: specify personal OpenAI-compatible model settings
* | 9a206db fix(b3): define relation prompt contract and verify live DeepSeek closure
* | cf467bf feat(b3): wire compatible provider and persisted planning graph UI
* | 94ad097 fix(b2v): preserve publication history and enforce draft/run CAS
* | d299e87 docs(b2v): 报告补充远端落地 SHA 与 tree 等价说明
* | f36e538 docs(b2v): B2-V 验收报告（§一–§八，378 测试通过）
* | 7da6ce1 feat(b2v): 发布边界修复 + 第一条业务垂直切片（§二–§七）
|/
* b9e9cb0 docs(b2c): B2-C 业务契约收口验收报告
* dbbb214 feat(b2c): /api/v1 业务 DTO + OpenAPI 导出 + 前端类型生成（契约收口）
* bc0eece feat(b2c): 真实 PG 端口契约 PgPlanRepository（幂等/并发/回滚）
* ed11e05 feat(b2c): 主线/扩展确定性校验接入发布边界 + 公共资源/领域包单测
* 8953f73 fix(b2c): 迁移 0003 复合 project FK + 字段对齐 + 公共资源/主线/扩展表
* 75b8674 fix(b2c): 发布携带完整结构 + 废弃只回 draft_ref 的不完整编辑
* cd08d90 feat(b2): 新增业务域迁移 0002 与真实 PG 验收（B2 起步）
* 3721635 docs(b1): 修正 B1.2 验收报告口径
* b1b076d test(recovery): 新增强制崩溃跨进程恢复反例（J2）
* cfbc982 test(planning): 发布原子性回滚反例与发布记录字段语义
* da1d23e fix(agent_workflows): 编辑后校验与保存的是新内容，非法编辑不得进入可确认态
* 18a16a3 fix(pg-harness): 共享实例上只读复用既有角色，缺失/不匹配时安全拒绝
* f7a9e26 docs(b1): 更新 B1 验收报告（B1.1 修复轮）

## Post-fetch validation and stop point

Command: git fetch --prune origin — PASS (2026-09-30).
GitHub codex/b3-f1 expected SHA: 6e51dfb34da955604894731aece695acda248156.
Observed origin/codex/b3-f1 SHA: 6e51dfb34da955604894731aece695acda248156.
Initial local HEAD SHA: 1683cbf2a1daa939c730777c1e029557b3384db7.
Local master SHA: f30d194e66eebc401e2f4723fe1d2ac21933cf77.
origin/master SHA: a9c469eb140121bef78767045bb742b5781b0a7c.
HEAD tree: 1e4c1115c2e9efa8fae0d5f869509e98fdf982c9.
origin/codex/b3-f1 tree: 1e4c1115c2e9efa8fae0d5f869509e98fdf982c9.
Tree comparison: equal; commit SHA comparison: different.

Safety gate: BLOCKED before local branch recreation. The untracked .workbuddy/memory/2026-09-29.md and design-preview files are important local artifacts and are not included in a Git bundle. They were left untouched and are listed above. No tracked or staged changes existed, so no patch files were generated. Because the task requires no unsaved important workspace changes before Task 4 and requires stopping when a safety precondition is unmet, no later branch, tag, push, acceptance-document, or AGENTS.md tasks were run.

Destructive Git operations: none.
Force push: none.
Branch or tag deletion: none.
Real model invocation: none.


## Continuation — 2026-09-30

The previous BLOCKED stop was resumed only after copying and validating every untracked artifact outside the repository.

Artifact backup:
- External backup: D:\studyplan-local-artifacts-backup-20260930
- SHA256 manifest: SHA256SUMS.txt
- Source and backup inventories: 18 files each; relative paths, file lengths, and SHA256 hashes all matched (PASS).
- Artifacts were moved to D:\studyplan-local-artifacts-staging-20260930, then restored after branch alignment.
- Restored inventory: 18 files; paths, lengths, and SHA256 hashes matched the external backup (PASS).

Branch alignment:
- codex/b3-f1: 6e51dfb34da955604894731aece695acda248156, equal to origin/codex/b3-f1.
- backup/local-codex-b3f1-pre-sync-20260930: 1683cbf2a1daa939c730777c1e029557b3384db7.
- master: a9c469eb140121bef78767045bb742b5781b0a7c, equal to origin/master.
- backup/local-master-pre-sync-20260930: f30d194e66eebc401e2f4723fe1d2ac21933cf77.
- develop: 6e51dfb34da955604894731aece695acda248156, pushed and equal to origin/develop.
- fix/b3f2-1-hardening: 6e51dfb34da955604894731aece695acda248156, pushed and equal to origin/fix/b3f2-1-hardening.

Checkpoint:
- Annotated tag: checkpoint-b3f2-batched-fake-20260930.
- Tag object SHA: fed7469c0c9012781a88175345db3403ea94c6f8.
- Target commit SHA: 6e51dfb34da955604894731aece695acda248156.
- The tag was pushed to origin.

Acceptance evidence:
- Task 5 GitHub SHA: 3a769cd7f5d9bd66850de8f5f672e3cae45ec418.
- Task 6 GitHub SHA: e0e272ff92bb261b999e4cb2d4e67041cef18e0b.
- Task 7 GitHub SHA: 880362eb460dbf702402e9746e34cd8f7e06f86f.
- Final evidence alignment SHA: 6e51dfb34da955604894731aece695acda248156.
- Short SHAs in the initial local graph are pre-API-replay local SHAs, not GitHub remote SHAs.

Documentation changes in this continuation:
- Added root AGENTS.md with the approved Git Workflow.
- Corrected GitHub SHA references in docs/acceptance/b3f2/batched/Delivery.md and commands-and-status.md.
- This maintenance record was appended with the continuation status.
- No .gitignore changes were made; .workbuddy and design-preview remain untracked and are excluded from commits.

No reset, rebase, force push, branch deletion, tag deletion, product-code change, database change, or real model invocation was performed.
