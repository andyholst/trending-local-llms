# Proposal: openspec-backlog-cap

Issue: #938 — "openspec-check must FAIL the merge gate when 50 OpenSpec changes are
PR: #939
still ACTIVE — the backlog cap makes archiving mandatory" (owner directive, 2026-11-14).

## Why

`make openspec-check` re-validates EVERY active OpenSpec change on every PR and every
push to master (qa-validate `validate` job). The archive lifecycle (#779, #866) closes a
change only through the PR that closes its own issue; nothing bounds the tail. A change
whose issue stalled, a keeper drift, or a review-required change parked for weeks stays
ACTIVE forever — re-validated on every pipeline while its spec drifts from the tree. The
historical worst measured **84 active on disk** (the stale-index incident noted in
`qa-validate.yml`); today the tree holds 11 active / 261 archived with no ceiling.

## What Changes

- New deterministic gate `make openspec-backlog-check` (`scripts/openspec_backlog_check.py`),
  the ONE implementation of the count, the cap (`MAX_ACTIVE_OPENSPEC_CHANGES = 50`) and the
  verdict:
  - counts directories under `openspec/changes/` excluding `archive/`;
  - at or over the cap: **exit 1**, naming every active change with its `Issue:` (read from
    its `proposal.md`) and the exact remedy (`make openspec-record-pr ISSUE=<n> PR=<pr>`,
    keeper archive for the rest);
  - under the cap: prints `active=<n>/50` (visible headroom) and exits 0;
  - a missing `openspec/changes/` tree is a loud **exit 2**, never a vacuous clean.
- `openspec-backlog-check` becomes a PREREQUISITE of `make openspec-check`, the gate
  qa-validate already runs on every PR and push — so at 50 active changes no PR can
  auto-merge to `master` (rule 6d: bundled into the existing stage, no new job).
- `AGENTS.md` §6f gains ONE sentence naming the cap (rule-3c declared diff, declared on
  issue #938); `ARCHITECTURE.md` §6 row + regenerated inventory block.

## Impact

- `scripts/openspec_backlog_check.py` (new), `Makefile` (two lines),
  `tests/test_openspec_backlog.py` (new suite), `AGENTS.md` §6f, `ARCHITECTURE.md`.
- CI: no new job — the existing `validate` job's `make openspec-check` step now also
  executes the cap check.

## Not covered

- Auto-archiving stale changes: the cap makes archiving MANDATORY by failing the merge
  gate; it never archives anything by itself (archiving a change its PR does not close
  stays the #812-governed act).
- The per-change CLI validation itself (`openspec validate`) — unchanged.
