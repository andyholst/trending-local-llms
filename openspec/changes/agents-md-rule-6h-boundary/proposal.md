# Proposal: agents-md-rule-6h-boundary

Issue: #512

## Why

`ARCHITECTURE.md` and `scripts/architecture_check.py` gained a boundary under
#182: the guard proves **presence** and two **structural** cross-checks (every
`--only` stage list of a Makefile target matches `scripts/validate.py`'s stage
map, in both directions; §4's job tables/bullets match each workflow's real
`jobs:` keys, every real job is claimed, and every workflow has a §4 section)
— and it **cannot read prose** (a sentence that is wrong about a real target
passes). The checker's docstring states it, the tests lock it
(`test_validate_only_stage_lists_match_the_validator`,
`test_pipeline_job_names_match_the_workflow_job_keys`,
`test_doc_states_what_the_guard_does_not_prove`), and `ARCHITECTURE.md` states
it where the promise is made.

But `AGENTS.md` rule 6h (the rulebook) still lists presence filters only and
never says the guard cannot read prose or names the two structural claims; and
§8's `tests/test_architecture.py` row cites issues #178/#506 only. Rule 6h is
where a contributor learns what "the guard keeps this file true" means: with
the boundary in the description but not in the rulebook, the next reader
trusts the stronger promise — a prose claim the guard cannot check — and the
two documents disagree about the same guard, which is exactly the drift
`architecture-check` exists to prevent.

The write was refused in the run that found it (#182, surfaced by PR #511):
`AGENTS.md` is a protected agent-instruction file with no interactive approver,
so the boundary landed in `ARCHITECTURE.md` only and this issue was filed
(rule 6g).

## What Changes

- **`AGENTS.md` rule 6h** — after the presence-failure list, a sentence states
  the boundary: the guard proves PRESENCE and two STRUCTURAL claims, the
  rulebook names them (`--only` stage lists vs the validator's stage map; §4
  job names vs the workflows' real `jobs:` keys), and it cannot read prose —
  a wrong sentence about a real target passes.
- **`AGENTS.md` §8** — the `tests/test_architecture.py` row names the two
  structural checks and the three tests that lock them, and the boundary.

## Impact

Two rulebook passages. No code, no make target, no stage, no pipeline job, no
script, no image, no contract, no data: the checks and tests already exist on
master and `make architecture-check` is already green, so `ARCHITECTURE.md` is
unchanged and nothing else is touched.

Rule 3c is satisfied by this change being reviewable: the issue named the
exact sections and the exact claims, and the diff a reviewer signs off is
precisely those passages.

## Not covered (out of scope)

- Any change to `scripts/architecture_check.py`, its tests, or the generated
  `ARCHITECTURE.md` §10 block — none is owed; the boundary is already enforced
  and this change only makes the rulebook describe it.
- The `openspec/changes/openspec-markdown-flavor/` change already exists;
  nothing here touches the OpenSpec CLI.
- Other owed `AGENTS.md` sentences filed from the same session's runs — each
  is its own `tech-debt` issue with its own change (rule 6g).
