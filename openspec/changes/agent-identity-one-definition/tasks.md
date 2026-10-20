# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/agent_identity.py` holds the name, address and allowed sets
- [x] 3. `check_commit_authorship.py` imports them instead of keeping a copy
- [x] 4. `make git-identity` (+ `_git-identity`) is the seam every committing job calls
- [x] 5. The four workflow sites use the seam; no literal remains
- [x] 6. Guards: the seam, the absence of the literal, the sets being one definition, the target
- [x] 7. Both push harnesses map the seam to the real definition
- [x] 8. `ARCHITECTURE.md` target + script rows; `make architecture-check` green
- [x] 9. Verified RED on the pre-change tree (13 failures) and GREEN after (728 checks)
- [x] 10. `OPENSPEC.md` regenerated; `make lint`, `make test`, `make openspec-check` green
