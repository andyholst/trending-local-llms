# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit, with its proposal, capability spec and this checklist
- [x] 2. `scripts/openspec_duplicate_check.py` parses each active change's capability specs and FAILS (exit 1) on a heading shared by two DIFFERENT changes under the SAME kind (ADDED∩ADDED / MODIFIED∩MODIFIED), naming both, the capability and the heading — while ADDED∩MODIFIED passes
- [x] 3. `make openspec-duplicate-check` runs the script, and `make openspec-check` depends on it
- [x] 4. `tests/test_openspec_duplicate_check.py` drives the real script: the #375/#371-style ADDED pair fails naming both; ADDED+MODIFIED (the firecrawl/outage shape) passes; a MODIFIED∩MODIFIED pair fails; unrelated changes pass; the real repo passes; the wiring is asserted
- [x] 5. The fixture pair is RED on the missing script (a module import error is not a green) and GREEN with the real script
- [x] 6. `OPENSPEC.md` regenerated (`openspec-index`) so the new change is listed
- [x] 7. `ARCHITECTURE.md` describes the script and the `openspec-duplicate-check` target (rule 6h)
- [x] 8. `AGENTS.md` §8 row added for the new guard (protected file, review-required)
- [x] 9. `findings.md` written (rule 6g)
- [x] 10. `make openspec-check`, `make lint`, `make test`, `make architecture-check`, `make secret-scan` green
