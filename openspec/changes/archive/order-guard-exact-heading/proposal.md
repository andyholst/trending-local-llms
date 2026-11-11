# Order-guard anchor must equal the exact README 'Most loved' heading

**Issue:** [#718](https://github.com/andyholst/trending-local-llms/issues/718)
**Capability:** `order-guard-exact-heading`

## Why

The #708/#711 order guard anchors on a stale, incomplete heading. After #713
merged as `d3b5b01`, `scripts/validate.py` defines `_MOST_LOVED_HDR` as only the
prefix `## ❤️ Most loved open-weight models on X`, but the canonical producer
heading — `scripts/update_trending.py:1747` and the committed `README.md:144` —
is the full:

```markdown
## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)
```

The owner flagged it verbatim on #713: the exact full heading "is still there in
the readme." Because the constant is only a prefix of the real heading, the
guard's absent-section decision (`_MOST_LOVED_HDR not in text`) and its section
split (`text.split(_MOST_LOVED_HDR, 1)[1]`) are anchored to something that does
not equal the producer's actual output. The prefix happens to be a substring of
the real README heading so current data still matches — but the anchor must equal
the producer heading exactly for the guard to be correct and future-proof.

## Delivery

- `scripts/validate.py` — set `_MOST_LOVED_HDR` to the exact README heading
  `## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)`
  (equals `README.md:144` and the renderer source `update_trending.py:1747`).
  The rest of `check_models_order_matches_readme` — the absent-section
  report-SKIP path and the strict `re.findall` divergence check — is unchanged.
- `tests/test_validate.py` — `test_models_order_matches_readme` builds its
  synthetic README with the same full heading so the self-contained test
  exercises the real anchor; skip-case (README without the full heading →
  not enforceable) and the strict present-but-divergent case still hold.
- `openspec/changes/order-guard-exact-heading/` — this change dir.
