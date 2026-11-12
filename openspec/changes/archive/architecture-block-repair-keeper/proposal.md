# Event-driven keeper for a red master ARCHITECTURE block gate

**Issue:** #861
PR: #868
**Capability:** `architecture-inventory` (the generated §10 block of
`ARCHITECTURE.md`, its guard `architecture-check`/`architecture-bot --check`,
and the pipeline keeper that repairs block drift the moment a merge causes it).

## Why

`make architecture-check` is a gate of qa-validate's `validate` job, which runs
on a **push to master** too. Any merged PR that adds or removes a make target,
a script or a workflow job moves the tree the §10 inventory describes, and a
change that forgot `make architecture-refresh` reds the push-to-master
`validate` **by construction** — the same failure shape #304 removed for
`OPENSPEC.md`. Measured 2026-11-12, in the implementation of #856 (`91eb093`):
the container suite failed with `FAIL repo: ARCHITECTURE.md's block matches the
tree — tree '11 pipelines, 201 make targets, 71 files in scripts/' vs on disk
'…199…70…'`. A red master `validate` has no PR-side repairer (rule 6q) and
auto-merge of EVERY open PR waits behind it; the only keeper named for this
gate is `architecture-bot`, cron `13 * * * 3` — Wednesday-only — so the queue
sits red for hours-to-days. The generated pair (`OPENSPEC.md` + the §10 block)
drifts from the SAME event; today one half is repaired in minutes
(`index-repair`) and the other only on Wednesday.

## What Changes

- `scripts/architecture_block_repair.py` — the ONE classifier+repair (rule 6d):
  `--classify-and-write` prints exactly one machine-checkable verdict
  `DRIFT=none|block-only` and regenerates ONLY the §10 block through the shipped
  generator (`scripts/architecture_bot.py`) when the drift is block-only;
  re-verifies with the generator's own comparison; exits 2 LOUDLY (never a
  silent clean, never a write) when the tree itself is malformed
  (`_flow_problems`/`_arch_calls_problems` findings), when `ARCHITECTURE.md` is
  missing, or when its `BEGIN`/`END` markers are gone.
  `--print-pr-body` composes the keeper PR body: no closing keyword (rule 6e),
  `refs #861`, naming the exact red run.
- qa-validate gains the `architecture-repair` job — the sibling of
  `index-repair` of the same shape: runs only after a FAILED `validate` on a
  push to master, needs `guard` first (rule 6j), classifies through
  `make architecture-block-repair`, and lands a keeper PR (branch
  `ci/architecture-block-repair-<UTC>`, owner PAT, never draft, never merges
  itself, one keeper per drift) only when `ARCHITECTURE.md` is the ONLY changed
  file.
- `make architecture-block-repair` + `make architecture-block-repair-pr-body`
  (host targets, stdlib only — the same seam `architecture-refresh` uses),
  wired to that job (rule 6m).
- `scripts/master_alarm.py`'s `GATES` names the new keeper for
  `architecture-check`: `qa-validate architecture-repair + architecture-bot`
  (the event-driven repairer first, the weekly backstop second).

## Impact

- `scripts/`: one new script (`architecture_block_repair.py`).
- `.github/workflows/qa-validate.yml`: one new job (`architecture-repair`).
- `Makefile`: two new public targets.
- `scripts/master_alarm.py` + `tests/test_master_alarm.py`: the keeper mapping.
- `tests/test_architecture_block_repair.py` (new suite) and
  `tests/test_workflows.py` (pins the new job's shape).
- `ARCHITECTURE.md` §4 job row, §3 target rows, §6 script row, regenerated §10;
  `AGENTS.md` §6q keeper sentence (declared on #861 per rule 3c); `OPENSPEC.md`
  regenerated.

## Not covered

- A keeper for `openspec-archive-check` stranding (an active change whose PR
  merged) — that drift class is tracked in its own issue #866.
- Prose repair: the keeper NEVER edits hand-written sections; only the generated
  block between the markers. A red whose cause is prose or a malformed tree
  stays red for a human/§6r.
- The weekly `architecture-bot` stays as the backstop; its cadence is unchanged.
