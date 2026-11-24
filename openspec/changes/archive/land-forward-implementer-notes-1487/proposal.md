# Proposal: land-forward-implementer-notes-1487

Issue: #1487
PR: #1489

## Why

The `M:198901c7` sync left `make fleet-host-sync-check BASE=origin/master` red on four lane skills. All four are base + additions with zero deletions, but only `tll-implementer` carries genuinely new experience; the planner/reviewer host copies are duplicated or interleaved fragments of bullets already on master, and the pr-rebase delta is only a host stamp. Copying host bytes to master verbatim would reintroduce the duplicate-bullet defect issues #1455, #1456 and #1469 were filed to remove.

## What Changes

- Three curated, additive bullets land in `agents/tll-implementer/skills/tll-implementer/SKILL.md`: the rule-3c protected-instruction dispatch handover, the `$GITHUB_EVENT_PATH` runner-path/host-side gate rule, and the concurrent-writer/worktree-collision rule. None duplicates a master bullet; the two orphan host fragments are not copied.
- A guard test in `tests/test_fleet_lifecycle.py` asserts each new note is present exactly once and that the orphan clause's copy count did not grow to two. It is registered in the module's hand-rolled `main()` (rule 6d).
- No AGENTS.md, contract, Makefile, workflow, data or image change.

## Impact

Additive documentation + one offline test. The other three lane skills stay host-ahead and still need their own curated landing; this change does not wipe or overwrite any host file.

## Not covered

- No refresh of the host profiles from master (that follows a merge, not this PR).
- No CI dispatch, merge, master push, collaborator grant or owner ruling.
