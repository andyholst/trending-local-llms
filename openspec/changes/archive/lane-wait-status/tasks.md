# Tasks: lane-wait-status

- [x] Add the while-you-wait status rule to AGENTS.md §7b with the rule 3c declaration note — verified by reading the section and the issue declaration comment
- [x] Add the status rule and `user@hostname` stamp to all seven lane SOULs and the planner skill — verified byte-for-byte additions only (`git diff --stat`: 9 files, 9 insertions)
- [x] Extend `tests/test_fleet_handover_protocol.py` with the two needles for all eight files — verified green on the branch and RED on `origin/master` (15 failures)
- [x] Add the AGENTS.md §8 guard row for issue #1232
- [x] Run lint / architecture / openspec / findings gates and regenerate the generated indexes
- [x] Full local `make test` green
