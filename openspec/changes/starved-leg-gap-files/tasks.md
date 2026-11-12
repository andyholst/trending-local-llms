# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `analyse()` groups raw snapshots by backend and newest 8-digit run date and computes `starved_legs`
- [x] 3. `starved_leg:<backend>` joins the signature (backend only, stable across refreshes) and a loud `STARVED LEG` finding names count + date
- [x] 4. A single empty snapshot in a capturing leg stays informational only
- [x] 5. `report["maintenance"]["starved_legs"]` carries the detail
- [x] 6. New guards `test_a_whole_starved_leg_changes_the_signature` + `test_a_single_empty_snapshot_stays_informational`, registered in the standalone runner
- [x] 7. Guards verified RED against the pre-change `analyse()` (suite dies with `KeyError: 'starved_legs'` on the stashed old script) and GREEN after (`PASSED 238 | FAILED 0`)
- [x] 8. AGENTS.md §4 + §8 carry the amended rule (rule 3c disclosure posted on #856)
- [x] 9. `OPENSPEC.md` regenerated; `make lint`, `make data-gaps`, `make findings-check`, `make architecture-check` green; the affected suites run green in the container (`test_data_gap_analysis` 238, `test_validate` 188, `test_architecture` 67, `test_architecture_bot` 53, `test_bot_markers` 57, `test_makefile_only` 25, `test_search_budget` 54, `test_worktree_base` 123, `test_pipeline_failure_guard` 26; the full `make test` runs in qa-validate's test image)
- [x] 10. Branch pushed and PR opened with the message pattern closing #856, `make pr-message-check` green locally before opening (qa-validate gates the rest)
