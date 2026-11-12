# Tasks

- [ ] 1. `scripts/secret_scan_report.py` — the ONE fileset verdict (rule 6d): parse the gitleaks JSON report, classify each finding with `git check-ignore`, fail (1) on committable findings, pass (0) naming gitignored artifacts, refuse (2) on a missing/unparsable report.
- [ ] 2. `Makefile` `_secret-scan`: write the JSON report (`--report-format json --report-path`), `--exit-code 0` for gitleaks, run the filter as the verdict, delete the report in the same recipe.
- [ ] 3. `.gitignore` + `scripts/issue_bot_working_files.txt`: the report file joins the ONE working-files list (rule 3d).
- [ ] 4. `scripts/secret_scan_self_test.py`: the third direction — the planted fake in a gitignored `__pycache__/` of a real throwaway git repo must stay green, the same fake in a tracked file must go red.
- [ ] 5. `tests/test_secret_scan.py`: recipe-shape pins (report written, filter decides, report deleted) + `test_scan_report_filter_decides_the_fileset` end-to-end against real git + probe pins for the new refusal strings.
- [ ] 6. `AGENTS.md` §3d (the fileset rule + the measured #836 failure) and the §8 guard row; rule-3c disclosure comment posted on the issue.
- [ ] 7. `ARCHITECTURE.md` (rule 6h): the new script row; `make architecture-refresh` + `architecture-check` green.
- [ ] 8. Verified: `make test`, `make lint`, `make secret-scan` green WITH `__pycache__` artifacts present on the host tree (the measured failure state), `make secret-scan-self-test` green, `make openspec-check`, `make validate` green.
- [ ] 9. `findings.md` written (`make findings-check`); `OPENSPEC.md` regenerated (`make openspec-index`).
