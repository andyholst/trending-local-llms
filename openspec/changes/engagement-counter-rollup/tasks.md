# Tasks: engagement-counter-rollup (issue #1182)

- [x] T1: additive cumulative-counter rollup in recompute_7d_engagement (MAX, rule 3b; rank semantics untouched).
- [x] T2: shipped store repair — 220 raises / 68 rows, flash-next 0→19,516 likes; README re-rendered.
- [x] T3: tests/test_engagement_rollup_1182.py (11 checks incl. RED proof on the pre-change seam).
- [x] T4: regressions — 7day 114/0, cross-model 98/0, engine-figure 32/0, validate QA PASSED, lint green.
- [ ] T5: PR opened, `make pr-message-check`, `make openspec-record-pr ISSUE=1182 PR=<pr>` at the PR head.