# Tasks

- [x] 1. Write the proposal + GWT capability spec for issue #718 (`order-guard-exact-heading`: `_MOST_LOVED_HDR` must equal the exact README 'Most loved' heading).
- [x] 2. Confirm the defect: `scripts/validate.py` `_MOST_LOVED_HDR` is only the prefix `## ❤️ Most loved open-weight models on X`; the committed README.md:144 + renderer update_trending.py:1747 carry the full `## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)`. Owner flagged it verbatim on #713.
- [x] 3. `scripts/validate.py` — set `_MOST_LOVED_HDR` to the exact full heading (equals README.md:144 / update_trending.py:1747); the absent-section SKIP path and the strict `re.findall` divergence check are unchanged.
- [x] 4. `tests/test_validate.py` — `test_models_order_matches_readme` synthetic README uses the same full heading; skip-case (no full heading → not-enforceable) and swapped-rows case still hold.
- [x] 5. Verify: `python3 tests/test_validate.py` PASSED 183/0; `python3 tests/test_make_commands.py` PASSED 11/0; real-store probe → HDR in README True, 117/117 rows matched, 0 FAILURES.
- [x] 6. `OPENSPEC.md` regenerated (`order-guard-exact-heading` active); `make openspec-check` green; `make lint-fix` last (all committed files end in a newline); commit authored `Andy Holst <andy.holst@protonmail.com>`.
