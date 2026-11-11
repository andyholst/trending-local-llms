# Tasks

- [x] 1. The tracked change exists (this dir) before any code edit
- [x] 2. New guard test `test_flatten_engagement_equals_posts_value_for_value` in tests/test_measurements_split.py proves, for every row resolved by `flatten_store(catalog, measurements, posts)`, that each of the five engagement counters equals `posts[source_post]` **value-for-value** (not merely non-shrinking), and that a row with no canonical post entry resolves to 0
- [x] 3. The guard runs on the REAL shipped data files (catalog + measurements + posts) — no logic mocks; the external-call rule is unchanged
- [x] 4. The non-shrink guard (`check_no_value_loss` / `check_split_flatten`) is kept; it still protects the #463/#525/#411/#650 loss classes against a drop
- [x] 5. `openspec/changes/measurement-store-normalized/proposal.md` no longer claims `README.md byte-identical`; it discloses that engagement-derived buzz/trend lines are re-resolved from canonical posts.json (the intended GWT2 consequence) and the README is regenerated accordingly
- [x] 6. `openspec/changes/measurement-store-normalized/specs/catalog-measurements/spec.md` scenario is retitled so t/s bands + card-fit match while engagement-influenced lines are re-resolved from posts.json (GWT2)
- [x] 7. `README.md` regenerated to the re-resolved engagement values and committed (honest artifact)
- [x] 8. `make lint-fix` run before commit so the first CI `validate` is not red on trailing newlines; commits authored `Andy Holst <andy.holst@protonmail.com>`
- [x] 9. `make test`, `make validate` (readme/data/schema), `make openspec-check` and `make lint` all green on the PR head
