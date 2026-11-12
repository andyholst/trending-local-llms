# Tasks: architecture-block-repair-keeper

- [x] Write `scripts/architecture_block_repair.py` (`--classify-and-write` verdict `DRIFT=none|block-only`, exit 2 refusals; `--print-pr-body` no-closing body)
- [x] Wire `make architecture-block-repair` + `make architecture-block-repair-pr-body` into the Makefile (public targets, `.PHONY`, host stdlib seam)
- [x] Add the `architecture-repair` job to `.github/workflows/qa-validate.yml` (sibling of `index-repair`: guard-first, failed master push only, only-ARCHITECTURE.md gate, dedup, owner PAT, never merges)
- [x] Name the new keeper in `scripts/master_alarm.py`'s `GATES` for `architecture-check`
- [x] New suite `tests/test_architecture_block_repair.py` (block-only rewrite, none, unbacked-tree refusal, missing markers/document, keeper body closes nothing, target wiring)
- [x] Extend `tests/test_workflows.py` with `test_architecture_repair_job_is_the_sibling_keeper_for_a_red_master_architecture_gate`
- [x] Extend `tests/test_master_alarm.py` with `test_the_architecture_gate_names_the_event_driven_keeper`
- [x] Update `ARCHITECTURE.md`: §4 job row, §3 target rows, §6 script row; regenerate the §10 block with `make architecture-refresh`
- [x] Update `AGENTS.md` §6q keeper sentence (declared on #861, rule 3c)
- [x] Regenerate `OPENSPEC.md` (`make openspec-index`) and pass `make openspec-check` + `make openspec-index-check`
- [x] Full suite green (`make test`) and `make lint` green in the container
- [x] Open the PR (message pattern, `closes #861` single keyword), monitor the pipeline to green/auto-merge
