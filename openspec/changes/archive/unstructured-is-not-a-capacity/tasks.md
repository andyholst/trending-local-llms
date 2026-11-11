# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `weight_gb`'s text pattern requires a weights word near the capacity
- [x] 3. `skip_fields` exists and `weight_gb` skips `hardware`; the haystack builder honours it
- [x] 4. Guard: card VRAM / unified memory are not prose weights, a stated footprint is
- [x] 5. Measured on the store: unstructured weight_gb 18 -> 3
- [x] 6. Verified RED on the pre-change analysis (2 failures) and GREEN after (131 checks)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-check` green
- [x] 8. `make lint` and `make test` green
