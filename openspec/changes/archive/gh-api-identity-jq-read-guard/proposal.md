# Proposal: gh-api-identity-jq-read-guard

Issue: #1711
PR: #1719

## Why

Slice A (#1683) registered 13 no-projection `gh api` REST reads in `scripts/gh_json_fields.py`, but the 5 identity `--jq .[]` sites whose per-line JSON objects are picked in Python were explicitly deferred. Measured on freshly fetched `origin/master` = `6163bed6e4dc8f86d04d32fa24373213016a7912` (module blob `fd57014f869edee538387d5470ee23f218505e8d`): all five are real, none is covered by slice A, and a `.get("created_at")` rename answers `None` for a renamed REST field, failing only at RUN time. The signed design `7155364626` measured that attributing the shared `issue_thread.render` reader to the comments answer false-reds whole-object `title` at `issue_thread.py:80`; the `blocked` partition is required for zero false reds.

## What Changes

- Add 5 `ApiPythonReadSite` records to the EXISTING `API_PYTHON_READ_SITES` in `scripts/gh_json_fields.py` for `announce_image_fallback.py`, `issue_thread.py`, `owed_rows_check.py`, `pipeline_failure_issue.py` and `sweep_outcome.py`, all at the existing `issues/{}/comments` family. Re-measured line numbers on this base: `57/74`, `108/84-86`, `67-68/57-58`, `1329/1377,1651,1959`, `125-126/132-133`.
- Add `user` and `login` to the existing `API_PYTHON_FIELDS["issues/{}/comments"]` set (the other recorded names were already there); no new family, extractor, signature or CLI flag.
- Use the existing `blocked` field to keep the whole-object half of `issue_thread.render` / `owed_rows_check.thread` out of the identity answer's source set, so neither half false-reds and no site is double-counted.
- Pin the pre-change module as `tests/fixtures/gh_json_fields_base_1711.py` (recorded blob `fd57014f869edee538387d5470ee23f218505e8d`, commit `6163bed6e4dc8f86d04d32fa24373213016a7912`), never an unconditional `git show origin/master:`.
- Add `tests/test_gh_json_fields.py::test_identity_jq_pick_rename_is_caught`, `::test_all_18_registered_reads_match_tree`, `::test_shipped_jq_projections_still_green` and `::test_fixed_origin_master_arm_is_green_1711`, all wired into `main()`.
- Extend the `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row with the 5-site clause and the pin, and write `findings/1711.md` with the site table, planted RED/GREEN file:lines, discovery totals and exclusions.

## Impact

Additive and non-breaking: 5 registry records, 2 field names and a `blocked` partition on the same registry. No data, schema, contract, API, table, workflow, Makefile, `--json` field set, `--jq` endpoint shape or product-behaviour change. `--scan` stays exit 0 / 0 findings with discovery 31 token-lists / 17 projecting / 14 not and exactly 5 identity `.[]` projections; slice A's 13 records and all 17 shipped `--jq` verdicts keep their behaviour.

## Not covered

- Slice C: dynamic-endpoint family resolution (`watch_monitor.py:253` `repos/{}/{path}` over `("issues", "pulls", …)`, `actions/runs?per_page=30`, `commits/master`).
- Slice D: the full static dataflow analyzer over ~1,404 `.get()` literals, helper returns, generic loop elements and cross-function parameters.
- The 2 genuine no-field sites, the latent `sweep_outcome.py:132` `createdAt`/`created_at` spelling mismatch, and any workflow, schedule or label change.
