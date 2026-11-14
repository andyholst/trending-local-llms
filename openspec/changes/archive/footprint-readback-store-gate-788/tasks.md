# Tasks: footprint-readback-store-gate-788

- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks)
- [x] Data reconciliation: 5 flagged values corrected to their capture's stated figure,
      17 declared with the canonical `(est)` marker (measurements.json + models.json mirror)
- [x] Scan precision: two-way structured same-field confirmation, bracket-stripped norm,
      `(est)` exclusion + `source_post_declared_estimates` in the report line
- [x] Shipped-store residue test (real scan, real store, per-flag attribution) — 0 flags
- [x] Planted-drift test proving the shipped gate goes red (the #531 class)
- [x] Precision tests with their opposite cases (unmarked value, cross-field value,
      longer prose tail all still flagged)
- [x] AGENTS.md §8 guard row + §4 `(est)` convention (rule 3c diff declared on the issue)
- [x] `make lint` green, `make secret-scan` clean, `make openspec-check` + index green
