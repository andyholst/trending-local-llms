# Proposal: small-delivery-rule-1839

Issue: #1839

## Why

At the freshly fetched base `f1692a1ff3eb3a12d67a4732ce776756d3d6f3a7`, `docs/fleet-collaboration.md` §3 and §4 item 4 describe lane remits and "one issue, one worktree, one branch" but never state the owner-mandated #690 delivery rule: every PR is a small, single-purpose, non-breaking delivery for one issue, with a breaking change split or flagged before writing. Six lane SOULs carry that rule; the canonical reader-facing doc does not, so a new clone on another host can bundle a schema or data-shape change into a doc PR and still believe it followed the protocol.

## What Changes

- Add ONE sentence to `docs/fleet-collaboration.md` §4 item 4 naming the #690 rule: small, single-purpose, non-breaking, one issue per PR, no unrelated churn or dead code, split or flag a breaking change before writing.
- Add ONE distinctive needle to `COLLAB_NEEDLES` in `tests/test_fleet_lifecycle.py`. The existing guard `test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol` iterates that tuple, so the sentence is pinned with no new test function and no change to `main()`.
- Add this tracked change (proposal, one capability spec with Given/When/Then scenarios naming the real guard, ticked tasks), record the analysis in `findings/1839.md`, and regenerate `OPENSPEC.md`.

## Impact

Purely additive documentation plus one source-level needle. No data, schema, contract, rulebook, Makefile, workflow, script, schedule or cron edit. No existing key, value or rule is removed or narrowed. The §6 cross-link owed in #1834 is untouched — it stays serialized behind #1835's owner decision.

## Not covered

- No second doc, no README table hand-edit, no AGENTS.md / SOUL / SKILL edit (rule 3c), no CI dispatch, no merge and no push to `master`.
- #1834's §6 cross-link and any breaking schema change are not fixed here.
