# order-guard-exact-heading

## ADDED Requirements

### Requirement: the order-guard heading anchor equals the exact README 'Most loved' heading

The order guard `check_models_order_matches_readme` (issue #708/#711) anchors its
absent-section decision and its section split on a heading constant
`_MOST_LOVED_HDR`. That constant MUST equal the producer's actual "Most loved"
heading exactly — the full string the renderer emits
(`scripts/update_trending.py:1747`) and the committed `README.md:144` carries:

`## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)`

A stale prefix constant (e.g. dropping the `(ranked by trend: 7-day buzz +
speed)` parenthetical) is a defect the owner flagged verbatim on #713: the guard
must anchor on the real heading so the absent-table report-SKIP and the strict
0-divergence order check are correct and future-proof.

WHEN the order guard runs against a README,
THEN it anchors on the exact full "Most loved" heading,
AND a README lacking that heading is reported as not-enforceable (SKIP),
AND a present-but-order-divergent README is still strictly caught.

#### Scenario: the heading constant equals the committed README heading

- **Given** the committed `README.md` and `scripts/update_trending.py` render source
- **When** the guard's `_MOST_LOVED_HDR` is compared to the README heading
- **Then** they are equal (the full `## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)`)
- **Test:** real-store probe — `_MOST_LOVED_HDR in README.read_text()` is True, 117/117 rows matched, 0 FAILURES

#### Scenario: a README without the full heading is skipped (not failed)

- **Given** a placeholder README with no 'Most loved' section
- **When** the order guard runs against a store
- **Then** it report-SKIPs (not enforceable) and records no failure
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (skip case)

#### Scenario: a present but order-divergent README is still caught

- **Given** a synthetic README with the full heading whose 'Most loved' rows are swapped
- **When** the order guard runs against the store order
- **Then** it fails, naming the divergence positions (strict path unchanged)
- **Test:** `tests/test_validate.py::test_models_order_matches_readme` (swapped-rows case)

#### Scenario: the real committed store/README still passes 0-divergence

- **Given** the real store and the committed README
- **When** the order guard runs
- **Then** it reports 0 divergences (117 models)
- **Test:** real-store probe — 0 FAILURES, HDR in README True, 117/117 matched
