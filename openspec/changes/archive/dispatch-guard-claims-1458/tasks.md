# Tasks: dispatch-guard-claims-1458

- [x] Extend `scripts/dispatch_guard.py` with the per-lane `claims` rows and the `--claim`/`CLAIMS=` overlap check (refuse an ACTIVE lane's overlapping path, naming the holder; allow a FINISHED lane).
- [x] Refuse a non-repo-relative claim (absolute/in-repo, `~`, `..`) while keeping every existing refusal (closed issue, merged bound PR, ceiling, in-repo registry) intact.
- [x] Forward `CLAIMS="p1 p2"` through `make dispatch-check`; keep a no-claim invocation byte-for-byte the old behaviour.
- [x] Add offline fixture tests for allow / refuse-active / allow-finished / refuse-in-repo plus the CLI and make seams — no network, no credential values.
- [x] Run `python3 tests/test_dispatch_guard.py`, `make lint`, `make architecture-check` and `make openspec-check`; regenerate `OPENSPEC.md`.
- [x] Open the PR ready for review with `Closes #1458` in BOTH the title and the body; post the PR-and-handover comment on the issue.
