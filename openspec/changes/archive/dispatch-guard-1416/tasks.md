# Tasks: dispatch-guard-1416

- [x] Add `scripts/dispatch_guard.py` with the stale-target guard (CLOSED issue / MERGED bound PR) and the one-constant concurrency ceiling over a caller-owned registry outside the repo.
- [x] Wire `make dispatch-check ISSUE=<n>` forwarding REGISTRY / CEILING / REPO / FROM_FILE / JSON, exit non-zero on refusal with the reason.
- [x] Add fixture tests for open / closed / merged PR / at-ceiling / over-ceiling, the CLI exit codes, `--help`, the in-repo registry refusal and the make seam — no network, no credential values.
- [x] Run `python3 tests/test_dispatch_guard.py`, `make lint`, `make architecture-check`, `make openspec-check` (offline half) and `make test`.
- [x] Add the `dispatch-check` / `scripts/dispatch_guard.py` / guard rows to `ARCHITECTURE.md` via `make architecture-refresh` and regenerate `OPENSPEC.md` with `make openspec-index`.
- [x] Open the PR ready for review with `Closes #1416` in both title and body; post the PR-and-handover comment on the issue.
