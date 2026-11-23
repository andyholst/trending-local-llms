# Tasks: dedupe-mirrors-1468

- [x] Measure the fetched base (`e27c774c`) and diff the planner/implementer mirrors against base `84cace0b` and the host copies
- [x] Remove the union-invented repeated phrases, the mid-sentence splice, the doubled Owner-directive paragraph and the dangling fragment in the planner mirror
- [x] Remove the dangling `chasing it.` duplicate in the implementer mirror
- [x] Drop the three pre-existing duplicate bullets so no mirrored bullet repeats
- [x] Prove zero duplicate sentences, lines and blocks across all four mirrors
- [x] Run `tests/test_fleet_lifecycle.py` and `make lint` green on the head
- [x] Regenerate `OPENSPEC.md` and pass `make openspec-check`
