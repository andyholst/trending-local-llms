# Tasks

- [x] 1. Write the proposal + GWT capability spec for issue #711 (`order-guard-fixture-tolerant`: order guard report-SKIPs only when the README lacks the 'Most loved' table; present-but-divergent still strictly caught).
- [x] 2. Confirm the current shape: `check_models_order_matches_readme` at `scripts/validate.py` still `fail("README has no 'Most loved' table")` on an absent section (strict, merged shape from #708/#710 @ `dc45207`); 5065c61 orphan held the report-skip split.
- [x] 3. `scripts/validate.py` — replace the absent-section `fail` with a `SKIP:` print + `return`; keep the strict `re.findall` divergence check byte-identical to the merged shape.
- [x] 4. `tests/test_validate.py` — add the skip-case to `test_models_order_matches_readme` (placeholder README → no FAILURES); keep the matching-passes-0-div and swapped-rows-caught cases green.
- [x] 5. Verify scoping: absent-section → SKIP (no fail); present-but-divergent → still FAILURES==1 "order != README" (strict path unchanged); real committed README/store → 0 divergences.
- [x] 6. Verify: `python3 tests/test_validate.py` PASSED 183/0 (incl. skip case); `python3 tests/test_make_commands.py` PASSED 11/0 (fixture path no longer red).
- [x] 7. `OPENSPEC.md` regenerated (`order-guard-fixture-tolerant` active); `make openspec-check` green; `make lint-fix` last (all committed files end in a newline); commit authored `Andy Holst <andy.holst@protonmail.com>`.
