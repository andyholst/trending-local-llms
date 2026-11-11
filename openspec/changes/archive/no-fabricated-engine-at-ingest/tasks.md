# Tasks

- [x] 1. The issue is filed with the measured row; the comment records that the prompt already forbids it (#458)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `fabricated_engine_reason` — quant token OR model-id substring, registry-aware
- [x] 4. `refuse_fabricated_engines` — (kept, refused-with-post)
- [x] 5. `ingest_raw_snapshots` refuses them, one loud line per row, post named
- [x] 6. A genuinely new engine is NOT refused (validation still reds for a human)
- [x] 7. `AGENTS.md` §4 rule + §8 guard row (rule 3c: rulebook change, review-required)
- [x] 8. Tests: both spellings, model-id name, registered kept, new engine kept, real ingest end-to-end
- [x] 9. Verified RED on the pre-change ingest and GREEN after (200 checks)
- [x] 10. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 11. `findings.md` written (rule 6g)
