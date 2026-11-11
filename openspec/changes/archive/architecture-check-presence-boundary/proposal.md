# Proposal: architecture-check-presence-boundary

Issue: #182 (`tech-debt: Presence, not description: architecture-check cannot see a wrong description`)

## Why

`scripts/architecture_check.py` compares **names**: a public target must be mentioned, a
described target must exist, every workflow and script must be named somewhere. Measured on the
base this change was cut from: adding a false sentence about a real target to
`ARCHITECTURE.md` (e.g. "`make merge` runs in the test image") leaves `make
architecture-check` green — the check cannot read prose.

That limit is real and worth stating, but the file's own promise ("the description is kept
true") reads stronger than what the guard proves. Two of the claim shapes it *cannot* see are
in fact machine-checkable, and are not checked today:

- the `--only` stage lists of the `validate*` targets vs. the stage map inside
  `scripts/validate.py` (a stage renamed in the validator, or a target's list rotted to a
  stage that no longer exists, is invisible to every guard);
- the **job names** in `ARCHITECTURE.md` §4's pipeline tables vs. the workflows' real `jobs:`
  keys. Measured: `queued-alarm.yml` defines `guard` and `alarm`, while §4 listed a `sweep`
  job for it that never existed (the `pr-health` sweep it described lives in another
  pipeline). Every guard stayed green.

## What Changes

- **`scripts/architecture_check.py`** grows two structural checks (no prose reading, no model):
  - `validate_stages()` reads the stage map out of `scripts/validate.py` **by AST** (every
    `add(label, stage, fn)` registration), and the Makefile's `--only` lists are compared with
    it in both directions: a list naming a stage the validator does not register fails, and a
    registered stage selected by no `--only` list fails (rule 6d's own contract, now also
    guarded at the description).
  - `described_jobs()` reads the job names §4 claims for each workflow — the `Job` tables and
    the bold job bullets — and compares them with the workflow's real `jobs:` keys, parsed by
    `scripts/architecture_bot.workflow_jobs` (ONE parser, not a second copy). A described job
    the workflow does not define fails; a real job no §4 section names fails; a workflow with
    no §4 section of its own fails (so the job coverage can never be vacuous).
- **`ARCHITECTURE.md`**: the guard's boundary is documented where the promise is made (what it
  proves: presence + these two structural cross-checks; what it does not: whether a sentence
  about a real target is true), and the stale `sweep` job row in the `queued-alarm` section is
  corrected (the second step is named inside `alarm`, where it actually runs).
- **`AGENTS.md` rule 6h**: the rulebook's version of the boundary is recorded in `findings.md`
  instead of written here — the file is protected and this run has no approver (see *Not covered*).
- **`tests/test_architecture.py`**: the new checks are driven against fixture trees (a rotted
  `--only` list, a stale job row, a missing job row) and a scenario fails when the fixture is
  right, so the guard is proved non-vacuous. Both new checks were run against the pre-change
  guard, which reports the same fixture GREEN — the assertions are not vacuous.

## Impact

`scripts/architecture_check.py`, `ARCHITECTURE.md`, `tests/test_architecture.py`, this OpenSpec
change and the regenerated `OPENSPEC.md`. No make target is added or renamed: the checks ride the
existing `make architecture-check` (`qa-validate`'s `validate` job, the fix loop and `make test` —
rules 6d/6m). No data file, contract, workflow, pipeline job or image changes.

## Not covered

- **`AGENTS.md` rule 6h and §8's row.** The rulebook carries the same boundary, but `AGENTS.md`
  is a protected file this run cannot write (the write is refused without an interactive
  approver). The boundary therefore lands in `ARCHITECTURE.md` — the document whose promise it
  qualifies — and the missing rulebook wording plus the §8 row are recorded in `findings.md` so
  they become their own tracked issue, per rule 6g.
- **Reading prose.** A false sentence about a real target ("`make merge` uses the test image")
  still passes. Making that mechanical would mean deriving the paragraphs, which is the same
  mistake in the other direction: a generator can only repeat the tree, never explain it.
- **A job's inner steps.** §4 describes what a job does in prose (`make` targets inside it); a
  step renamed inside a job is out of reach for the same reason. The `make` targets a job calls
  are covered by §10's generated block (#479), not by this guard.
- **The images' contents.** §5's table is prose about Dockerfiles; nothing here checks it.
