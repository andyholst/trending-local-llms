# Tasks: engine-figure-alignment-795

- [x] Triage issue #795 against the fetched base (triage.md, verdict implement)
- [x] Record `ENGINE_NAME_ALIASES` + `canonical_engine_name` in
  `scripts/engine_registry.py` (ONE spelling map, decisions stated in comments)
- [x] Resolve captured spellings in `register_new_engines` so `make engine-check` is
  WARN-free for aliased spellings (unregistered targets keep the WARN)
- [x] Fold the registry map into `update_trending.apply_engine_aliases` (model-specific
  aliases still win) and accept a declared spelling in `fabricated_engine_reason`
- [x] Record the Bonsai Oryon + mlx.fast decisions in the `data/models.json` engine
  registry notes (additive)
- [x] Justify every shipped cross-row duplicate pair with `measurement_model_aliases` in
  `data/models.json` (rule 3b additive — no row removed, no value shrunk; verified by a
  key-by-key walk of base vs new store: 39 keys added, 1 note extended, 0 removals)
- [x] Add `cross_row_duplicate_measurements` + the failing `check_no_duplicate_measurements`
  gate to `scripts/validate.py`, registered in the `data` stage (rule 6d wiring)
- [x] `tests/test_engine_figure_alignment.py` locking every scenario (runs the real
  scripts, no mocks of them — rule 6m)
- [x] Add the `AGENTS.md` §8 regression-guard row for the new suite
- [x] Run the gates green: `make validate`, `make test`, `make lint`, `make engine-check`,
  `make openspec-check`
- [x] Commit, push, open the PR (`closes #795`) — reviewable, never a draft, never merged here.
- [~] This change archived on its own closing head by `make openspec-record-pr ISSUE=795 PR=<pr>` — blocked: the PR number exists only after `gh pr create`; the record runs on this branch immediately after opening (rule 6f's required shape)
