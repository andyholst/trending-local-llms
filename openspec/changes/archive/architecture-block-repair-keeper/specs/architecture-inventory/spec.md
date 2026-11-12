# architecture-inventory

## ADDED Requirements

### Requirement: a red master ARCHITECTURE block gate has an event-driven keeper with a script-owned verdict

When the push-to-master `validate` goes red at `architecture-check`, qa-validate's
`architecture-repair` job SHALL run `make architecture-block-repair` against the
exact post-merge tree, and the verdict SHALL belong to
`scripts/architecture_block_repair.py` (rule 6d): it prints exactly one
`DRIFT=none|block-only` line. Only a `block-only` verdict may land a keeper PR;
the job SHALL run only after the `guard` and only on a FAILED push to master;
the keeper PR SHALL carry ONLY the regenerated `ARCHITECTURE.md` and SHALL never
merge itself. A missing `ARCHITECTURE.md`, a missing `BEGIN`/`END` marker pair,
or a tree the generator refuses to describe SHALL exit 2 naming the refusal —
never a silent clean, never a write.

#### Scenario: the exact post-merge drift classifies block-only and the rewrite is current

- **GIVEN** a fixture tree whose committed §10 block predates a merged change
  (a new script and a new make target exist on disk; the block does not name them)
- **WHEN** `--classify-and-write` runs against that tree
- **THEN** it exits 0, prints `DRIFT=block-only`, the rewritten block equals the
  generator's own fresh render, and the ONLY file changed on disk is
  `ARCHITECTURE.md` (the prose above the markers is byte-identical)

- **Test:** `tests/test_architecture_block_repair.py::test_a_stale_block_after_a_merge_classifies_block_only_and_rewrites`

#### Scenario: a current block classifies none and writes nothing

- **GIVEN** a fixture tree whose §10 block is exactly what the generator would
  produce
- **WHEN** `--classify-and-write` runs
- **THEN** it exits 0 printing `DRIFT=none` and the `ARCHITECTURE.md` bytes are
  untouched (the red had another cause; the workflow lands nothing)

- **Test:** `tests/test_architecture_block_repair.py::test_a_current_block_classifies_none_and_writes_nothing`

#### Scenario: a tree the generator refuses is refused loudly, never overwritten

- **GIVEN** a fixture tree whose described flow is not backed (a workflow job
  calls a `make` target the Makefile does not define) — block staleness and a
  real defect at once
- **WHEN** `--classify-and-write` runs
- **THEN** it exits 2, names the generator's own refusal, and
  `ARCHITECTURE.md` is byte-untouched (a keeper PR must not launder a broken
  tree with a rewritten block)

- **Test:** `tests/test_architecture_block_repair.py::test_an_unbacked_tree_refuses_exit_2_and_writes_nothing`

#### Scenario: a document without the generated block is not block drift

- **GIVEN** a fixture whose `ARCHITECTURE.md` carries no `BEGIN`/`END` marker
  pair (or is missing entirely)
- **WHEN** `--classify-and-write` runs
- **THEN** it exits 2 naming the missing markers / missing file, and nothing is
  written (regenerating a block the document has nowhere to hold is not a
  repair)

- **Test:** `tests/test_architecture_block_repair.py::test_missing_markers_or_document_exit_2_naming_the_refusal`

#### Scenario: the keeper job is the index-repair shape and the keeper mapping names it

- **GIVEN** qa-validate's shipped workflow and `scripts/master_alarm.py`'s
  `GATES` table
- **WHEN** the suite reads them
- **THEN** the `architecture-repair` job exists, needs `guard` and `validate`,
  runs only on `failure() && push && master`, classifies through
  `make architecture-block-repair`, lands its PR only when `ARCHITECTURE.md` is
  the only changed file, holds only `contents: write` + `pull-requests: write`,
  carries no `environment:` gate, and `GATES["architecture-check"]` names
  `qa-validate architecture-repair` alongside the weekly `architecture-bot`

- **Test:** `tests/test_workflows.py::test_architecture_repair_job_is_the_sibling_keeper_for_a_red_master_architecture_gate`
- **Test:** `tests/test_master_alarm.py::test_the_architecture_gate_names_the_event_driven_keeper`

#### Scenario: the keeper PR body records drift and closes nothing

- **WHEN** `--print-pr-body --master-sha <sha> --run-url <url>` composes the body
- **THEN** it names the red run and the classification, carries NO closing
  keyword (the real closure parser finds zero closes), and `refs #861` only;
  without `--master-sha`/`--run-url` it exits 2

- **Test:** `tests/test_architecture_block_repair.py::test_the_keeper_body_records_drift_and_closes_nothing`
