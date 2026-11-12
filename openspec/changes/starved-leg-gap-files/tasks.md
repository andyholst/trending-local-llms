# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `analyse()` groups raw snapshots by backend and newest 8-digit run date and computes `starved_legs`
- [x] 3. `starved_leg:<backend>` joins the signature (backend only, stable across refreshes) and a loud `STARVED LEG` finding names count + date
- [x] 4. A single empty snapshot in a capturing leg stays informational only
- [x] 5. `report["maintenance"]["starved_legs"]` carries the detail
- [x] 6. New guards `test_a_whole_starved_leg_changes_the_signature` + `test_a_single_empty_snapshot_stays_informational`, registered in the standalone runner
- [x] 7. Guards verified RED against the pre-change `analyse()` (suite dies with `KeyError: 'starved_legs'` on the stashed old script) and GREEN after (`PASSED 238 | FAILED 0`)
- [x] 8. AGENTS.md §4 + §8 carry the amended rule (rule 3c disclosure posted on #856)
- [ ] 9. `OPENSPEC.md` regenerated; `make lint`, `make data-gaps`, the standalone gap suite and the full suite in the container green
- [ ] 10. Branch pushed and PR opened with the message pattern closing #856, `make pr-message-check` green locally before opening (qa-validate gates the rest)
