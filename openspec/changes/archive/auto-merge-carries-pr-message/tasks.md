## 1. Pipeline fix

- [x] 1.1 `auto-merge` merge step reads the merged PR's title+body (`gh pr view --json title` / `--json body`) and passes `--subject` + `--body-file` (verified: `make test` `test_auto_merge` green on the new step)

## 2. Tests lock the fix

- [x] 2.1 `test_auto_merge` guards the title+body read, `--subject` and `--body-file`; verified RED against the pre-fix step (`git show origin/master:.github/workflows/qa-validate.yml`) and GREEN on the fixed step

## 3. Docs scroll

- [x] 3.1 `ARCHITECTURE.md` §4 auto-merge row names the title+body hand-off (verified: `make architecture-check`)
- [x] 3.2 `AGENTS.md` §8 regression-guard row for the #787 class (lands the owed row `S8` of issue #787)
