# Repository Workflow

## Git Workflow

- `master` is the stable milestone branch. It receives only accepted milestone
  merges from `develop`.
- `develop` is the only long-lived integration branch.
- AI agents must not commit directly to `master`.
- Start each Goal from `develop` on a short-lived `feat/<goal>`, `fix/<goal>`, or
  `docs/<goal>` branch.
- A Goal may contain multiple meaningful commits. When it is complete, merge its
  branch into `develop` with `git merge --no-ff`.
- Preserve useful implementation history; do not squash meaningful commits by
  default.
- Merge to `master` only after the corresponding `develop` milestone has been
  accepted.
- Never rebase or force-push published `master` or `develop` history. Do not
  force-push shared history.
- Before destructive Git operations, record `git status --short`, `git branch
  -vv`, and `git log --graph --decorate --oneline --all`; verify remote SHAs and
  create a recoverable backup branch, tag, or bundle.
- Use annotated `checkpoint-*` tags for important intermediate states and
  annotated `milestone-*` tags for accepted releases.
- Acceptance documents may identify a remote commit only with a SHA that exists
  on GitHub. If a commit was replayed through the GitHub API, explain why its
  remote SHA differs from the original local SHA.
- Report test states only as `PASS`, `FAIL`, or `NOT RUN`.
- Never rewrite a published database migration; add a new migration instead.
- Do not run real paid-model validation unless the user explicitly authorizes it.
