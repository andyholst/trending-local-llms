# Proposal: renovate-json5-parse-guard-1870

Issue: #1870

## Why

`renovate.json5` is named `.json5` on purpose (#716): it carries the rule-6t / #1029 `//` comments that explain why the weekly auto-bump cadence lives app-side and why no Renovate workflow may own an `on.schedule`. Renovate reads that extension natively; renaming it to `renovate.json` would make the comments invalid and break the config. The defect is in the guard, not the config: `tests/test_workflows.py::test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron` reads the file as text and uses `re.search` / substring checks. It never parses. Measured on base `1c3cd933`: a config with trailing commas and a missing closing brace passes all seven text checks while `json.loads` rejects it. A future syntax break would stay green and silently disable the weekly auto-bump and dependency dashboard with no alert.

## What Changes

- Add one small, tested helper `json5_to_json` in `tests/test_workflows.py` that reduces the JSON5 subset the config uses to strict JSON: it strips `//` and `/* */` comments and trailing commas while respecting string literals and escaped quotes, then the guard calls `json.loads` on its output. No `json5` module, no network install, no edit to `renovate.json5`.
- Replace the guard's regex/substring assertions with assertions on the PARSED object: a weekly `schedule`, an explicit string `timezone`, `enabledManagers` containing both `github-actions` and `dockerfile`, and `separateMultipleMajor` / `dependencyDashboard` both `True`. Keep the existing per-workflow "no Renovate `on.schedule`" loop byte-for-byte.
- Add a direct test of the stripper (URL with `//`, `/*` inside a value, commas/braces inside strings, escaped quotes, trailing commas in arrays and objects) and call both new functions from `main()`.

## Impact

Tests-only. No data, schema, contract, README, workflow, image, Makefile target or rulebook change. `renovate.json5` is not edited; its extension and its `//` comments stay exactly as they are. The existing guard names and the workflow-cron checks are preserved; one parse check and five parsed-value checks replace five substring checks.

## Not covered

- No rename of `renovate.json5` and no relaxation of rule 6t / #1029 — refresh-bot stays the only workflow with a cron.
- No rulebook §8 row is written here (AGENTS.md is protected in a headless leg); its full text is declared on the issue as review-required.
- No general JSON5 implementation: only the comment and trailing-comma forms this config actually uses.
