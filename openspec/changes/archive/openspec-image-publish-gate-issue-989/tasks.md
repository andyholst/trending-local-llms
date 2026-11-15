# Tasks: openspec-image-publish-gate-issue-989

- [x] Flip the `openspec-image` job gating in `refresh-bot.yml`: `Build + push` on `publish_openspec == 'yes'`, `already current — skip rebuild` on `== 'no'` (mirror of the base `built == 'yes'` gating) — VERIFIED by the flipped `if:` in both steps.
- [x] Make both `tests/test_workflows.py` pins step-name-keyed (`step(job, "Build + push the OpenSpec image")["if"]` / `step(job, "already current")["if"]`) so they assert each step's actual gate — VERIFIED: the suite passes 1107/0 on the fixed workflow.
- [x] Prove the new pins are red on the OLD wiring — VERIFIED: both named checks FAIL when `origin/master`'s `refresh-bot.yml` is planted in place, green again when restored.
- [x] `make test`, `make lint`, `make openspec-check`, `make architecture-check`, `make pr-message-check` green on the branch — VERIFIED locally (see PR).
