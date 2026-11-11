# Tasks

- [x] 1. The tracked change exists (this dir) before any code edit
- [x] 2. `openspec/changes/measurement-store-normalized/tasks.md` line 10 no longer claims `README.md byte-identical`; it discloses the README is regenerated from the flattened view with engagement-derived buzz/trend lines re-resolved from canonical `data/posts.json` (intended GWT2, corrected on issue #699)
- [x] 3. No phrasing in the corrected tasks.md contradicts the corrected proposal.md/spec disclosure
- [x] 4. No code change, no schema change, no data change, no README regeneration beyond the already-merged artifact
- [x] 5. `make openspec-check` green; the change is listed in `OPENSPEC.md` (index regenerated)
- [x] 6. `make lint-fix` run before commit; commit authored `Andy Holst <andy.holst@protonmail.com>`; commit-authorship OK
- [x] 7. `make test` green and PR opened ready for review; never self-merge (qa-validate merges when validate + live-smoke are green at the head)
