# Proposal: refuse-fix-round-self-archive

Issue: #812 — `tech-debt: A fix round can archive an open PR's own OpenSpec change before its PR merges`
PR: #901

## Why

Rule 6f archives an OpenSpec change only when the PR it names has **merged**;
`make openspec-archive-check` (issue #779) is the gate that reds an ACTIVE change
naming a merged PR before the merge. A fix round that archives the very change it
is mid-fixing dismantles that trail — and does it **silently**: with the change
moved to `openspec/changes/archive/`, `make openspec-check` validates the
self-consistent archived index, `make openspec-archive-check` reads only the
ACTIVE changes it no longer contains, and the fix loop reports success over a
change it has dismantled.

Measured (issue #812, filed while implementing #621): round 1 of the fix loop ran
`make openspec-archive` on this branch's own change `spec-test-lines-verified`
while PR #621 was still open and unmerged — `git status` before repair showed the
deleted active change dir, `+ openspec/changes/archive/spec-test-lines-verified/`,
and `OPENSPEC.md` re-pointed to `#810` ("Active changes: 16 → 15"). The archive
moved a PR number that did not yet exist.

The loop cannot intercept every path a Hermes round may take — a round runs
arbitrary `make` targets inside the agent. What the loop CAN do is refuse the
**result**: snapshot which changes are active, and after every round detect and
undo a baseline-active change gone from the tree, before any green re-check can
exit 0 on the dismantled state.

## What Changes

- **`scripts/self_archive_guard.py` (new).** `snapshot` records the OpenSpec
  changes active on disk NOW (JSON: `active` + `archive` names) at
  `SELF_ARCHIVE_BASELINE`; `check` compares the tree against that baseline and
  exits 1 naming every baseline-ACTIVE change gone from `openspec/changes/` —
  with `SELF_ARCHIVE_RESTORE=1` it restores first: a fresh copy under
  `openspec/changes/archive/` is moved back and the index re-staged (`git add -A
  -- openspec/changes`), otherwise the files are brought back from
  `SELF_ARCHIVE_REF`, otherwise the loss is reported `unrecoverable`, never
  silent. A missing baseline exits 2 (a guard that cannot read its baseline must
  not pass vacuously, rule 6c).
- **`scripts/fix_loop.sh` wiring.** After `merge_base` (a base merge may
  legitimately archive the base's changes — those belong to the baseline, never
  to a dismantle) and only inside a git checkout, the loop snapshots the baseline
  and exports `SELF_ARCHIVE_REF=HEAD`; after EVERY round — before the green
  re-check at the top of the loop can `exit 0` — it runs
  `SELF_ARCHIVE_RESTORE=1 make self-archive-guard`: a dismantle (exit 1) is
  restored, its report folded into the next round's repair notes (`$NOTES`), and
  a guard that could not run (exit 2) is itself recorded in the notes.
  `arch-calls:` names both targets.
- **`Makefile`**: `self-archive-snapshot` / `self-archive-guard` (host-only git
  gates, the `check-commit-authorship` pattern — rule 6d: one script, reached
  only through these targets).
- **Tests (rule 6c).** `tests/test_self_archive_guard.py` drives the REAL script
  against planted trees: clean green; move-into-archive reported and restored; a
  change already archived at the baseline is NOT a dismantle; a COMMITTED mid-run
  move is restored and re-staged in the index; a vanished change is restored from
  the reference; unrecoverable loss is loud; missing baseline is a loud exit 2; a
  change created after the snapshot is this run's own artifact, not guarded.
  `tests/test_fix_loop.py::test_a_round_that_archives_its_own_change_is_refused_and_restored`
  drives the REAL loop in a REAL git repo whose stub round performs the measured
  dismantle (the recorder moves `openspec/changes/foo` into `archive/`), runs the
  REAL guard script, and asserts: baseline snapshotted, guard ran after the
  round, the round is named, the change is back on disk, the fresh archive copy
  is gone, and the loop goes on and still lands green. The fixture simulates the
  round's effect (rule 6m: the system under test — the loop, the guard, git — is
  real; only the LLM round is the sanctioned stand-in).
- **Docs**: the `AGENTS.md` §8 guard row (rule 6c) and `ARCHITECTURE.md`'s two
  target rows + §6 script row (rule 6h).

## Impact

`scripts/fix_loop.sh`, `scripts/self_archive_guard.py` (new),
`tests/test_self_archive_guard.py` (new), `tests/test_fix_loop.py`, `Makefile`,
`AGENTS.md` §8, `ARCHITECTURE.md` (§4 targets table, §6 scripts table, §10
regenerated block), `OPENSPEC.md`. No pipeline job, workflow, image or data
format changes; additive only (rule 3b).

## Not covered

- **Rounds that archive a DIFFERENT change** (one whose PR merged this run): the
  guard baselines the whole active set, so archiving a change whose merge the run
  legitimately records is visible to `make openspec-record-pr`, not to this
  guard — this guard refuses only what this run dismantles mid-loop.
- **A human archiving early**: `make openspec-archive` stays available outside a
  fix run; `openspec-archive-check` (#779) remains the merge-time gate.
- **The OPENSPEC.md row the dismantling round rewrote**: the guard restores the
  change directory; the index itself is forced back into agreement by the
  deterministic `openspec-index-check` gate in the next check pass, not by the
  guard.
