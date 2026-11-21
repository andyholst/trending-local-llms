# Tasks — weekly-free-model-refresh (issue #1195)

- [x] `scripts/free_model_refresh.py`: live read by NAME, free-step-only update (append/retire/handover/context), non-free tiers byte-untouched, measured + additive refresh_history, no-op writes nothing, exit 2/1 refusals, --dry-run, --pr-body
- [x] Makefile: `_free-model-refresh` / `free-model-refresh` / `_free-model-refresh-pr-body` / `free-model-refresh-pr-body` (internal recipe + public wrapper pattern)
- [x] `refresh-bot.yml`: deterministic `free-model-refresh` job (needs guard, owner PAT checkout, base-check, refresh, render, `make keeper-pr` landing) on the existing Wednesday cron — rule 6t: no second scheduled pipeline
- [x] `tests/test_free_model_refresh.py`: real script vs a real local HTTP server — PASSED 36 | FAILED 0 (behaviour, refusals, keeper body, wiring)
- [x] `tests/test_workflows.py` PASSED 1190 | FAILED 0 and `tests/test_makefile_only.py` PASSED 25 | FAILED 0 with the new job/targets
- [x] Live end-to-end proof: `make free-model-refresh` against the real Nous catalogue (credential by name) → `no change: the live free set (5 models) equals the chain's — nothing written`, tree clean
- [x] ARCHITECTURE.md: §2 target rows, §4 refresh-bot job row, §6 script row, base-check prose corrected; `make architecture-refresh` for §10
- [x] AGENTS.md §8 row added (rule 3c attended sign-off, comment on #1195)
- [x] OpenSpec change: proposal, capability spec with Test lines, this checklist
- [x] `findings.md` written, `make findings-check` green, findings filed (`make file-findings` → #1204 host re-provisioning gap)
- [x] `make lint` + `make architecture-check` green
- [x] `make openspec-check` green (index regenerated, binding, backlog)
- [~] Full suite (`make test`) green on the PR head — blocked: qa-validate runs it after push; on the host the new module (36) + test_workflows (1190) + test_makefile_only (25) are green
- [x] PR opened (#1205, five-section body, single `closes #1195`), `make pr-message-check` green, `make openspec-record-pr ISSUE=1195 PR=1205` so the archive sits at the PR head
