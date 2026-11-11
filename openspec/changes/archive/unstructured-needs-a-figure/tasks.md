# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `analyse()` scans each field on its own and never the engine registry's notes
- [x] 3. `context_tokens` requires a context-window figure the number modifies (`tok/s` and a bare `context`/`kv-cache` word excluded)
- [x] 4. `storage_offload` accepts only `flash storage|memory|drive`, never bare `flash`
- [x] 5. `weight_gb` refuses a capacity qualified as VRAM / RAM / unified memory / DDR
- [x] 6. Guards green after the change (168 checks) and RED on the pre-change analyser (14 failures)
- [x] 7. Measured on the store: context_tokens 6 -> 2, weight_gb 3 -> 2, storage_offload 1 -> 0; `missing` 30/36/44/58/35 unchanged
- [x] 8. AGENTS.md §3 bullet + §8 row could NOT be written (the sandbox protects AGENTS.md); the exact text is quoted in `proposal.md` under BLOCKED for a human to apply
- [x] 9. `OPENSPEC.md` regenerated; `make openspec-tasks-check`, `make openspec-index-check`, `make lint`, the full test suite, `make validate`, `make validate-mapped` and `make architecture-check` run (the docker-backed `openspec validate --changes` is reported where docker is absent)
- [x] 10. `findings.md` written and `make findings-check` green
