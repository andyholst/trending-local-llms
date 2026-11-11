# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `verify_closure.py` reads the merged PR's closing references and decides
- [x] 3. A missing state is fetched from the issue; a bounded retry covers GitHub's lag
- [x] 4. A `gh` failure is a loud exit, never a pass; closing nothing is not a failure
- [x] 5. `make verify-closure` (+ `_verify-closure`) and the `auto-merge` step
- [x] 6. Guard runs the real script against a stub `gh` (external system only)
- [x] 7. `ARCHITECTURE.md` (target row + job step) and `openspec-index` updated
- [x] 8. Verified RED on the pre-change tree (11 failures) and GREEN after (12 checks)
- [x] 9. `make lint`, `make architecture-check`, `make test` and `make openspec-check` green
