# Tasks: event-driven keeper for a red master index gate (#304)

- [x] 1. `scripts/openspec_index_repair.py`: `--classify-and-write` prints the
      one-line verdict `DRIFT=none|index-only`, regenerates through
      `openspec_index.py --write` only on index-only drift, re-verifies with the
      generator's own `--check`, and exits 2 loudly when a present index cannot be
      read; `--print-pr-body` composes the no-closing keeper body.
- [x] 2. `tests/test_openspec_index_repair.py` — 7 checks: index-only after a
      merge+archive, `none` writes nothing, missing file is index-only,
      unreadable is loud, the keeper body implements no issue under the REAL
      `pr_closure` parser, the Makefile/qa-validate wiring is one seam.
- [x] 3. `make openspec-index-repair` + `make openspec-index-repair-pr-body`
      defined (+ `.PHONY`) and called by qa-validate's `index-repair` job — no
      step reaches the script directly (rules 6d/6m).
- [x] 4. qa-validate `index-repair` job: `needs: [guard, validate]`, `if:
      failure()` on a push to `master` only, verdict read from the script (the job
      re-decides nothing), file-set boundary (`OPENSPEC.md`/`openspec/**` only),
      branch `ci/openspec-index-repair-<UTC>`, agent identity, owner PAT, no
      merge. Locked by
      `tests/test_workflows.py::test_index_repair_job_is_the_event_driven_keeper_for_a_red_master_index_gate`.
- [x] 5. `scripts/master_alarm.py` GATES names `openspec-check` →
      `qa-validate index-repair + architecture-bot`; `tests/test_master_alarm.py`
      pins the per-gate keeper mapping (green: `test_every_validate_gate_is_on_a_list`).
- [x] 6. AGENTS.md §6q names the event-driven keeper and §6b's `qa-validate.yml`
      row names the `index-repair` job (rule 3c: the same branch carries the
      AGENTS.md diff; review-required).
- [x] 7. ARCHITECTURE.md documents the two targets, the job row and the script
      row; §10 inventory regenerated with `make architecture-refresh`;
      `make architecture-check` green.
- [x] 8. `make openspec-index` regenerated; `make openspec-index-check` green.
- [x] 9. `findings.md` records the two gaps this run found (the stale HOURLY
      wording, the ARCHITECTURE.md half without an event-driven keeper) — filed
      as separate `tech-debt` issues, NOT fixed here (rule 6g).
- [x] 10. Full container suite green: `make lint` + `make test` in this worktree.
- [x] 11. Commit, push, open the PR (ready for review, never a draft), closing
      exactly #304 with the five-section body.
