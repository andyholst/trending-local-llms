## Tasks — #1164: a PR-blocking pipeline failure is recorded and its fix is gated

### Filer

- [x] `failure_shape(block, targets, steps)` — the normalised signature (run ids/SHAs/counts collapsed)
- [x] `open_pr_branches(repo)` — the OPEN PRs; a non-list answer is an empty set
- [x] `pr_triggered_failures(repo, window_hours, now)` — `--event pull_request` runs + job/log/block/shape
- [x] `group_pr_blockages(items, open_branches)` — one group per shape with ≥2 open PRs
- [x] `record_pr_blockages(...)` rides `sweep` through `make pipeline-failure-issue`; ONE issue per shape, ledger row with `trigger`/`failure_shape`/`blocked_prs`/`pr_count` ADDED

### Guard

- [x] `pipeline_failure_guard_check.verdict(..., now=None)` — a `trigger: pull_request` row is reported inside `PR_BLOCK_GRACE_HOURS` and RED past it
- [x] `_ts` reads the ledger's ISO8601Z `filed_utc` (a silent None would make every row fresh)

### Tests

- [x] `tests/test_pipeline_failure_issue.py` — shape normalisation, grouping, the real sweep end to end, idempotence, `--dry`
- [x] `tests/test_pipeline_failure_guard.py` — both sides of the grace, ISO8601Z, a landed fix clearing it, an unstamped row untouched
- [x] The stub `gh` serves an event-filtered run fixture and `pr list`, so the master fixture is never mistaken for a PR run list

### Rulebook (rule 3c — review-required)

- [x] `AGENTS.md` §6r: the PR-blockage pass under `make pipeline-failure-issue`, and the new refusal under `make pipeline-failure-guard-check`
- [x] `AGENTS.md` §8: both guard-table rows carry issue #1164
- [x] The rule-3c notice is posted on issue #1164 naming the sections and why

### Verification

- [x] `make test` green (host: 1 known quota-artifact red, `test_refusals_land_declaration.py`, reproduced on pristine `origin/master`; the container is the authority)
- [x] `make validate` green (`QA PASSED`)
- [x] `make lint` green (model-chain OK)
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (218-line inventory block, after `make architecture-refresh`)

### Scope boundary

- No new make target, pipeline job or image: the pass is bundled into `make pipeline-failure-issue` (rule 6d).
- A blockage hitting fewer than two open PRs stays that author's own noise, unrecorded.
