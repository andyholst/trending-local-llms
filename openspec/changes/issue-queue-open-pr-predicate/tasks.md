# Tasks: issue-queue-open-pr-predicate

- [x] Add `body` to the PR list seam and a `_closes_issue` helper using the ONE closure parser
- [x] Mark any issue closed by an OPEN PR as having an implementer, regardless of branch prefix
- [x] Fold the closing PR's timestamps into the reported implementer activity
- [x] Add RED-first guards: fix/-prefixed closing PR, unbound PR, parser shapes (RED on base verified)
- [x] Write `findings.md` and run the targeted test, `make lint`, `make findings-check` and `make openspec-check`
- [x] Regenerate `OPENSPEC.md`, commit, push and open PR #1310's reviewable PR with one closing keyword
