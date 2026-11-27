# Tasks: agents-file-findings-prepush-1806

- [x] Replace only the `tests/test_file_findings.py` (rule 6g, issue #172) row at `AGENTS.md:2381` with the owner-signed byte-exact text from design 7219073743
- [x] Verify each of the three `test_prepush_guard_*` names occurs exactly once in `AGENTS.md`, `fast offline pre-push guard` once, pipe count unchanged, exactly two module rows, and the line 2484 row untouched
- [x] Write `findings/1806.md` recording the missing §8 row, the owner sign-off and the done-when evidence
- [x] `findings-check-for-pr` pre-push guard green for this branch with `issue 1806` and the PR body
- [x] OpenSpec change (proposal bound to `Issue: #1806`, Given/When/Then spec with real `- **Test:**` references, all tasks ticked) + `OPENSPEC.md` regenerated
- [x] Fast offline gates green (`make lint`, `make openspec-check`, archive-check, targeted `tests/test_file_findings.py`)
- [x] PR opened READY with `Closes #1806` in title AND body; `qa-validate` merges on green `validate` + `live-smoke`
