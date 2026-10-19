# Proposal: fix-loop-notes-outside-tree

Issue: #390 — `tech-debt: the fix loop leaves qa-report.txt.notes in the repo tree and git add -A commits it`

## Why

The fix loop records what happened between rounds (a Hermes round killed by its own
timeout, a round that changed nothing) in a notes file that `run_checks` folds into
`qa-report.txt` — because `run_checks` truncates the report at the start of every
round, a note written straight into it would be wiped before anyone could read it.

Issue #383 introduced that channel as `NOTES="$REPORT.notes"` and created the file
unconditionally with `: >"$NOTES"` (`scripts/fix_loop.sh:36-37`). `REPORT` defaults
to `qa-report.txt`, i.e. the repository root, and `.gitignore` names `qa-report.txt`
and `comment.md` exactly — not the `qa-report.txt.*` class. The bot's commit step
stages with a plain `git add -A`, so the loop's scratch file was committed:

- measured on PR #387 (the implementation of #376): commit `622daee` adds
  `qa-report.txt.notes` — 0 bytes, blob `e69de29`. It is empty because that loop
  went green on round 1, so no note was ever written: empty was the *correct*
  content. The defect is that the file exists in the tree at all.
- the guards that should have caught it cannot see it. `tests/test_workflows.py::
  _run_push_step` runs the REAL commit step in a temp clone with the repo's
  `.gitignore`, but plants only `qa-report.txt` and `comment.md`; `tests/
  test_fix_loop.py` always points `QA_REPORT` at a temp directory, so the
  production shape (`qa-report.txt` in the cwd, which IS the checkout) is never
  exercised.

The loss is not only noise: a NON-empty notes file (the timed-out round this whole
channel exists for) would publish the loop's own diagnostics into the repository,
inside a data PR whose reviewer has no reason to expect them.

## What Changes

- **The notes live outside the checkout.** `scripts/fix_loop.sh` creates them with
  `mktemp` in `${TMPDIR:-/tmp}`, and removes them on exit (`trap … EXIT`). The
  channel itself is unchanged: `run_checks` still folds the notes into the report,
  so a timeout or a no-progress round is still visible where the PR comment reads it.
- **`.gitignore` covers the class**, not two exact names: `qa-report.txt.*` beside
  `qa-report.txt`. The loop no longer writes a sibling, and any future one cannot be
  swept into a commit by `git add -A`.
- **`tests/test_workflows.py`** plants `qa-report.txt.notes` in the temp clone the
  REAL commit step runs in and fails when it reaches the pushed commit.
- **`tests/test_fix_loop.py::test_scratch_notes_stay_out_of_the_tree`** runs the REAL
  loop with the production shape (`QA_REPORT=qa-report.txt`, relative), with a
  timed-out round so the note is non-empty, and asserts no `*.notes` file appears
  beside the report while the timeout still reaches `qa-report.txt`.

Both guards were verified RED against the pre-change tree (`git stash` of
`.gitignore` + `scripts/fix_loop.sh`): the loop leaves `['qa-report.txt.notes']`,
and the pushed commit carries `['data.json', 'qa-report.txt.notes']`.

Additive only in the data sense and narrower than that here: nothing is removed from
the product, no value is shrunk, no make target, stage, pipeline job or image is
added or renamed (`ARCHITECTURE.md` is unchanged, rule 6h). AGENTS.md §8 gains the
guard row this change is required to add (rule 6c).

## Impact

`scripts/fix_loop.sh`, `.gitignore`, `tests/test_fix_loop.py`,
`tests/test_workflows.py`, `AGENTS.md` (§8 guard row), this OpenSpec change and the
regenerated `OPENSPEC.md`.

## Not covered

- **Cleaning `qa-report.txt.notes` out of PR #387.** That branch is the issue-bot's;
  after this lands the file is ignored, but a file already tracked stays tracked, so
  the branch needs its own `git rm --cached` (or a re-cut) — a decision about a live
  bot PR, not this change (rule 6g: the finding is fixed here, the PR it soiled is
  repaired there).
- **The notes being re-folded on every later round.** A note from round 1 appears in
  round 2's and round 3's report, because the file is never cleared after folding.
  That is arguably the intent (each round's Hermes call must see why the previous one
  died) and changing it is a judgement about the prompt, not about where the file
  lives.
- **Every other scratch file the bots write.** The class fixed here is the loop's
  report siblings; the general question ("does every artifact a bot writes have a
  home outside the checkout or an ignore rule?") is wider than this defect.
