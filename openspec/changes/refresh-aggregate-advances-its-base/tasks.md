# Tasks

- [x] 1. The issue is filed FIRST with the measurement (run 39329834698)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `scripts/worktree_base.py advance` — fast-forward a clean checkout, refuse a dirty or diverged one
- [x] 4. `make base-advance` (host target) wired to that mode
- [x] 5. `refresh-bot`'s `aggregate` uses it, with the reason stated in the step
- [x] 6. `AGENTS.md` §6n rule + §8 guard row (rule 3c: rulebook change, review-required)
- [x] 7. `ARCHITECTURE.md` target row, `aggregate` job and script description (rule 6h)
- [x] 8. Tests against real git: advances, no-op, dirty refused, diverged refused, seam names the mode
- [x] 9. Verified RED on the pre-change script (6 checks) and GREEN after (74 checks)
- [x] 10. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 11. `findings.md` written (rule 6g)
