# Tasks

- [x] 1. Verify the defect is live on origin/master: no resolver reads a spec's `- **Test:**` reference, and `tests/test_agents_rows.py` exists but defines no `test_the_footprint_sentence_names_every_dimension` (the shipped RED fixture).
- [x] 2. `scripts/check_openspec_test_lines.py`: resolve every ACTIVE change spec's `- **Test:** <path>::<test>` (file exists, symbol defined top-level for a Python module), fail naming change + scenario line + missing target, report prose/no-reference lines, exclude archived changes.
- [x] 3. `tests/test_openspec_spec_tests.py`: prove RED on the shipped `tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension` reference, plus missing-file, prose-span, no-test-lines, archived-ignored, resolvable-green and real-repo-green/wired cases.
- [x] 4. `Makefile`: add `openspec-spec-tests-check` and bundle it into `openspec-check` (rule 6d).
- [x] 5. `AGENTS.md` §6f sentence gains the resolution requirement; §8 gains the guard row (protected file — review-required, rule 3c; announced on the issue).
- [x] 6. `ARCHITECTURE.md`: §3 target table row, §6 script row, and the generated §10 "Every script" line for `scripts/check_openspec_test_lines.py` (rule 6h); `scripts/openspec_index.py --write` regenerates `OPENSPEC.md` with this change's row.
- [x] 7. `findings.md` records any gap noticed (rule 6g).
- [x] 8. Run the host-run gates: the new test file, `scripts/openspec_index.py --check`, `scripts/architecture_bot.py --check`, `scripts/architecture_check.py`, and `bash scripts/run_tests.sh` for the affected modules.
- [x] 9. Commit, push, open the PR (ready for review, never a draft); `openspec-record-pr` records the PR number on this change once it exists.
