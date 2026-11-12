# Tasks: engagement-counter-mapping

- [ ] Name the counter mapping in the `data-search` skill (fixed page order, card
      omits-zeroes ambiguity, open-the-post-page rule, no-neighbour-card rule)
- [ ] Extend the skill-wording test to pin the new contract and prove it RED on the old skill
- [ ] `post_signal_coverage` returns the fourth metric (views > 0); `check_post_signal`
      prints `with views` coverage
- [ ] Views-coverage assertions in `tests/test_post_signal.py` (prove RED on the old helper)
- [ ] `make data-gaps`/`make validate` unaffected as verdicts; `make test`, `make lint`,
      `make openspec-check` green; `OPENSPEC.md` regenerated
