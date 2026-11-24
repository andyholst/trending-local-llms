# Tasks: findings-mixed-none-refusal

- [x] `scripts/file_findings.py::parse()` refuses the mixed shape (section + `- none`) with an error naming both, and keeps `- none`-only / sections-only behaviour byte-identical
- [x] `tests/test_file_findings.py` drives the REAL parser over planted files: mixed red, `- none`-only green, sections-only green, and the two shipped files reporting their real counts
- [x] the guard is RED-first: the new module run against `origin/master`'s `scripts/file_findings.py` reports the mixed-file check failing (`PASSED 88 | FAILED 3`; after the change `PASSED 91 | FAILED 0`)
- [x] the stray `- none` line dropped from `findings/1586.md` and `findings/1612.md`
- [~] AGENTS.md §8 row extended to name the mixed-shape guard — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared via the owed-row finding in `findings/1662.md`
- [x] `make openspec-index` regenerated; `make openspec-check` green
- [x] fast offline gates green (`make lint` rc 0, the targeted module 91/0) and the findings file `findings/1662.md` written
- [ ] PR opened with the five-section body and `Closes #1662`; the change archived/recorded on the branch; CI monitored
