# Tasks

- [x] 1. The tracked change exists (this directory) before any code or test edit
- [x] 2. `scripts/keeper_pr.py`: `--file` accepts a space-separated SET of owned
      files — ONE commit carries every owned file that changed, exit 0 when none
      changed, exit 1 when any change falls outside the set; a single file behaves
      exactly as before
- [x] 3. `architecture-bot.yml`'s land step becomes ONE `make keeper-pr
      FILE="ARCHITECTURE.md OPENSPEC.md" BRANCH_PREFIX=ci/architecture-refresh
      DEDUPE=1 … BODY_TARGET=architecture-pr-body` call; the hand-written
      branch/commit/push/body shell and its `make git-identity` step are deleted
- [x] 4. `tests/test_keeper_pr.py`: two multi-file landing tests (both files land in
      ONE commit; the partial set lands the file that changed) and the Done-when
      scan now covers `architecture-bot.yml:refresh`
- [x] 5. `tests/test_architecture_bot.py`: the shipped-run test executes the new
      land step through the real seam (stub `gh` answers `pr list`), pins the
      `ci/architecture-refresh-<UTC>Z` branch shape, and pins that the step names
      both generated files through `FILE=` and spells no landing shell of its own
- [x] 6. `ARCHITECTURE.md` §10 regenerated via `make architecture-refresh` on the
      changed workflow (rule 6h/#947), and `OPENSPEC.md` re-indexed
- [x] 7. Gates green on the exact head: `make lint`, `make test`,
      `make openspec-check` (binding + backlog + archive wiring),
      `make openspec-index-check`, `make architecture-check`
- [x] 8. PR opened with ONE closing keyword on #1081 and the five-section body;
      `make openspec-record-pr ISSUE=1081 PR=<pr>` archives this change at the PR
      head before auto-merge
