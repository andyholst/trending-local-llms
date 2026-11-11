# Proposal: blocked-task-is-visible

Issue: #409

## Why

`scripts/check_openspec_tasks.py` understands exactly two checkbox states: `- [ ]` (incomplete, the
gate fails) and `- [x]` (done). There is no third state for **work that is finished as far as the
agent may take it and is waiting on a human** — the AGENTS.md §8 row written into `AGENTS-ROW.md`
and filed for a person to apply, a signature under rule 3c, an approval that a bot must not give
itself. An implementer in that position has two exits, and both are worse than the gap:

- tick a box for work that was not done (the exact dishonesty #172's gate exists to catch), or
- leave `- [ ]` and keep `make test` / `make openspec-check` red for a change whose only remaining
  work is somebody else's signature.

Writing `- [~]` today does not fail and does not report: the regex only matches `[ xX]`, so the line
is **silently skipped** — the change is reported `OK … all tasks checked` while a task sits
unfinished, which is the failure mode the gate was built to prevent.

Measured against this tree before the change (2026-10-27, `origin/master` `f26f105`):

    $ mkdir -p /tmp/pr/changes/x && printf '# Tasks\n\n- [x] 1. done\n- [~] 2. blocked\n' > /tmp/pr/changes/x/tasks.md
    $ python3 -c "import check_openspec_tasks as m; print(m.check_all(base=Path('/tmp/pr/changes')))"
    [openspec-tasks] OK x: all tasks checked
    0

## What Changes

- **`scripts/check_openspec_tasks.py`** learns a THIRD state, `- [~] <text> — blocked: <who/why>`:
  - it is **accepted** (the gate does not fail on it),
  - it is **reported**, loudly, as `REVIEW-REQUIRED <change>: N task(s) blocked on a human`, with
    each blocked line printed, so it is neither counted as done nor silently skipped,
  - a `- [~]` with **no `blocked:` annotation** is a FAILURE (an unannotated blocked box is a
    silent skip wearing a third state), named by line.
  The exit code stays 0 when the only unfinished work is blocked-on-a-human, and 1 for any real
  `- [ ]` or any unannotated `[~]`.
- **`scripts/openspec_index.py`** counts the blocked boxes: a row whose checklist has them renders
  `done/total · N blocked`, so the change stays visibly incomplete in the one file a reviewer opens.
  A row with no blocked task renders byte-identically to today.
- **`Makefile`** — `openspec-check`'s closing line stops claiming "every task is ticked" (it would
  be false whenever a blocked box exists) and names the review-required report instead; the
  `openspec-tasks-check` help text describes the third state.
- **`ARCHITECTURE.md`** — the §3 target row and the §6 script row describe the blocked state.

## Impact

The task gate and the index generator, their two test modules, two Makefile lines and one
`ARCHITECTURE.md` description. No data, no contract, no workflow, no new target (so no new CI
wiring): `make openspec-check` keeps its exact job list and only becomes honest about what it found.

## Not covered

- **`AGENTS.md` rule 6f is NOT edited here.** It says `make openspec-check` requires "no unticked
  box", and the blocked state is a behaviour change to this file's own gate, so rule 3c applies: the
  issue must carry a comment naming the section and why, and a reviewer signs off on that diff.
  Issue #409 carries no such comment (its body is the whole thread, and it has none). The exact
  wording owed is written out in `findings.md` and filed as its own tech-debt issue instead of being
  written by this run.
- No `openspec` CLI change: `openspec validate` checks a change's STRUCTURE and does not read
  checkbox states (which is why this completion gate exists), so the third state needs no CLI
  support.
- Nothing about *who* may sign: the annotation is free text naming the human and the reason. This
  change does not verify that a named reviewer actually signed.
