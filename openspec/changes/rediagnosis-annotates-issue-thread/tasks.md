# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit; it binds `Issue: #987` and
      carries proposal, capability spec and this checklist
- [x] 2. `scripts/bot_markers.py` declares the `pipeline-rediagnose` marker shape via a dedicated
      writer + `run=` parser, and names it in `UNREGISTERED_OWED` with issue #987 (its AGENTS.md §6j
      row is owed to rule 3c — a protected file a headless leg cannot write)
- [x] 3. `scripts/pipeline_failure_issue.py`'s `rediagnose_undiagnosed()` posts ONE
      marker-deduplicated comment on the cited issue when a raise lands, quoting the scrubbed
      `error_excerpt` + `targets`; a raise with no cited issue is raised comment-free
- [x] 4. `tests/test_pipeline_failure_issue.py` drives the REAL filer against a stub `gh` proving:
      one comment carries the marker + excerpt + masked secret; a thread already carrying the marker
      is not double-annotated; a raise with no issue cites no thread; `--dry` writes no comment
- [x] 5. `tests/test_bot_markers.py` wiring asserts the marker is declared (UNREGISTERED_OWED names
      its issue) — the dedicated writer/parser round-trip and the reverse-scan acceptance stay green
- [x] 6. The owed AGENTS.md §6j table row is recorded in `findings.md` with the registered owed-row
      marker (rule 3c), and the tasks box is written blocked — rule 3c human sign-off
- [~] 6b. AGENTS.md §6j `queued-alarm` row names `pipeline-rediagnose` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] 7. Gates green on the exact head: `make openspec-check`, `make openspec-index`, `make test`,
      `make lint`, `make architecture-check`, `make validate-mapped`
