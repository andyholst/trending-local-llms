# Proposal: pr-closes-title-and-body-1838

Issue: #1838
PR: #1842

## Why

At the freshly fetched base `793bf6fa9b189d26832e554e9459f1cc8e1a6bf1`, `docs/fleet-collaboration.md:66` (added by #1833 / PR #1836) tells a reader that a PR opens READY with "exactly one closing keyword bound to their issue" but never says WHERE that keyword must appear. `AGENTS.md` and the lane SOULs carry the owner-mandated both-required rule, but this file is declared the canonical reader-facing protocol. A new bot on another host following it naturally writes a body-only PR; that PR can merge with every gate green and leave its issue open (#682 / PR #688), so the implementer to reviewer to close chain loses its closing bookend.

## What Changes

- Add ONE sentence to `docs/fleet-collaboration.md` section 4 item 4: the title carries the change and `Closes #<id>`, and the body repeats its own `Closes #<id>` line — never title-only, never body-only — so the squash closes the issue.
- Add ONE distinctive needle for that sentence to `COLLAB_NEEDLES` in `tests/test_fleet_lifecycle.py`. The already-rowed `test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol` iterates that tuple, so the new sentence is pinned without a second source of truth; no new test function is added and `main()` is unchanged.
- Add this tracked change (proposal, one capability spec with Given/When/Then scenarios whose `Test:` lines name the real guard, and a ticked task checklist), regenerate `OPENSPEC.md`, and record the analysis in `findings/1838.md`.

## Impact

Purely additive documentation plus one source-level needle: no data, schema, contract, Makefile, workflow, script, rulebook, schedule or cron edit. No existing key, value or rule is removed or narrowed, no new test function or `make` target is introduced, so `ARCHITECTURE.md` needs no change. Companion #1839 targets the same two files and stays QUEUED behind this PR; nothing in this change touches its scope.

## Not covered

- No `AGENTS.md` / SOUL / SKILL edit (rule 3c protects the rulebook in a headless leg), no second collaboration doc, no closing-binding implementation, no CI dispatch, no merge and no push to `master`.
- #1839's separate doc/test correction is not fixed here.
