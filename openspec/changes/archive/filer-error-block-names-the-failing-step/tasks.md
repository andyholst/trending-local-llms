# Tasks: filer-error-block-names-the-failing-step

- [x] `scripts/pipeline_failure_issue.py` — `log_regions` / `failing_region` / `failing_step_names`
      plus the tiered, failure-anchored `extract_error_block` (region label + `##[error]` anchor,
      selection by tier, presentation in log order, cap, a loud dropped-chatter note), the sweep and
      the re-diagnosis pass both passing the job, and the "no make target while the step is known"
      line.
- [x] `tests/test_pipeline_failure_error_block.py` — every scenario in the spec, driving the REAL
      filer against the planted log shaped like the measured run 43725338063 tail (rule 6m: a
      recorded fixture + the real `gh` stub on PATH, no `scripts/` rebinding).
- [x] `scripts/pipeline_failure_issue.py` — the ledger row records `failing_steps` and
      `error_region` additively (rule 3b: a new key, never a rewrite of a stored value).
- [x] `AGENTS.md` §6r + §8 — the extraction sentence now says the block is failure-anchored
      (region tiers, the two step sources, the additive `failing_steps`/`error_region` keys) and §8
      carries the guard row. Attended run: the rows land in THIS branch (rule 3c), and the review of
      this PR IS the sign-off — the issue thread states which sections changed (rule 3c).
- [x] Gates green on the branch head — `make lint`, `make secret-scan`, `make architecture-check`
      (with `make architecture-refresh` for the `scripts/` diff), `make owed-rows-check`,
      `make pipeline-failure-guard-check`, `make findings-check`, `make test` — verified locally on
      this head and re-run by `qa-validate` on the PR head.
