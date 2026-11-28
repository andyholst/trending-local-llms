# Proposal: multi-planner-dual-surface-1859

Issue: #1859
PR: #1861

## Why

At the freshly fetched base `d0f5dc5840e86db1a331734480397abebb3447ae`, `docs/fleet-collaboration.md` §1 says "The planner is the single dispatcher and stays ONE instance", §2 says a PR comment "mirrors it but transfers no ownership", and §5 says "Four instances per delegable lane" with a single planner. It describes one planner host and treats the issue thread as the only board. The owner's 2026-11-28 directive allows an unlimited number of tll-planner machines, each with its own tll agent lanes, collaborating through BOTH the issue comment threads AND the PR comment threads. Without a written dual-surface protocol, bots on different machines can double-claim a file or PR head, lose a handover, or assume a second dispatcher exists.

## What Changes

- Add §7 "Unbounded planner machines and dual-surface handovers" to `docs/fleet-collaboration.md`: unlimited tll-planner machines each with their own tll agent lanes; the comment threads as the ONE shared surface and single source of truth; every claim/status/verdict/handover/done on BOTH the issue's own thread AND the relevant PR comment thread; `user@hostname` machine stamps; newest-comment reads for live claims on ANY machine with the twice-claim guard and `make dispatch-check` lease; no cron, scheduler or second dispatcher.
- Cross-reference §7 from §1, §2, §4 and §5, and reconcile their earlier single-instance / issue-only wording with the directive.
- Add ONE guard test `test_the_collaboration_doc_covers_unbounded_planners_and_dual_surface_handovers` to `tests/test_fleet_lifecycle.py`, wired into `main()`; measured RED (7 missing needles) on the pristine doc and GREEN after the edit.
- Add this tracked change, `findings/1859.md`, and regenerate `OPENSPEC.md`.

## Impact

Docs and one guard test only. No rulebook/data/schema/renderer/workflow/schedule edit, no cron, no new Actions `schedule:`, no second dispatcher role.

## Not covered

- No in-tree `agents/` mirror change and no host SOUL/SKILL change (the planner updated its own host files first); no push to `master`, no hand-merge.
