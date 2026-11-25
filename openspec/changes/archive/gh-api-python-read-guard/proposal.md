# Proposal: gh-api-python-read-guard

Issue: #1683
PR: #1712

## Why

`scripts/gh_json_fields.py` validated `gh <cmd> --json` fields (#1158/#1160) and `gh api … --jq` paths (#1668/#1676), but #1675 narrowed its claim to say that a `gh api` answer whose fields are picked in PYTHON is OUT OF SCOPE. Measured on freshly fetched `origin/master` = `9faaa4695bbc707ea11f658093a1acbb84369b34`: 32 `gh api` read sites in `scripts/`, 18 naming a REST field in Python and unchecked. `.get("created_at")` answers `None` for a renamed field, so a REST rename fails only at RUN time — the exact build-time-vs-run-time hole the `--json` and `--jq` halves already closed.

## What Changes

- Add `API_PYTHON_FIELDS` (recorded REST answer fields per family) and `API_PYTHON_READ_SITES` (13 no-projection sites with their read scopes) to `scripts/gh_json_fields.py`, including the token-list-invisible `GH_API = ("gh", "api")` tuple splat at `refresh_run_block.py:105`.
- Add `api_python_read_problems(tree)` and ONE extra pass in `scan_file`, so a `.get()` or subscript pick on a registered site is re-derived from the real AST and compared with its recorded fields and family. No existing function signature changes; the `--jq` path is untouched; no other script under `scripts/` is edited.
- Add `tests/test_gh_json_fields.py::test_python_pick_rename_is_caught` (both `.get()` and `r["ref"]` plantings, RED on a pinned base module), `::test_registered_reads_match_tree` (13-site equality), `::test_shipped_jq_shapes_still_green` (exit 0 / 0 findings, 31/17/14) and `::test_fixed_origin_master_arm_is_green` (base pinned by a recorded blob, no moving-ref assertion).
- Pin the pre-change module as `tests/fixtures/gh_json_fields_base_1683.py` (recorded blob `9e96236b2aaa20005b9d8fa1be8d91489218c284`, commit `9faaa4695bbc707ea11f658093a1acbb84369b34`), so the RED arm is stable after merge and readable inside the test container.
- Land the matching `ARCHITECTURE.md` §6 row clause and `findings/1683.md` (13-site table, measurements, deliberate exclusions, one owed rulebook row).

## Impact

Additive and non-breaking: no data, schema, contract, API, table, workflow, Makefile or product-behaviour change. `--scan` stays exit 0 / 0 findings on the shipped tree, the 17 `--jq` verdicts and 31/17/14 discovery totals are unchanged, and the 5 identity `--jq .[]` sites plus the general `.get()` surface stay out of scope for their own later issues.

## Not covered

- The 5 identity `--jq .[]` sites and their Python picks (later slice B).
- Dynamic-endpoint family inference beyond the one registered `watch_monitor.py` site (later slice C).
- The full static dataflow analyzer over all ~1,404 `.get()` literals, helper returns and generic loop elements (later slice D).
- Any `gh --json` field set, `API_SHAPES` path, `check_argv` verdict, CLI flag, Makefile target or workflow schedule change.
