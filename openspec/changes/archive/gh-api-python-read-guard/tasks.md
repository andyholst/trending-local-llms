# Tasks: gh-api-python-read-guard

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist + `.openspec.yaml`)
- [x] Re-measure the site counts on freshly fetched `origin/master` `9faaa4695bbc707ea11f658093a1acbb84369b34` (32 read sites, 18 Python field reads, 13 no-projection incl. the `GH_API` splat; discovery 31/17/14)
- [x] Add `API_PYTHON_FIELDS` and the 13-record `API_PYTHON_READ_SITES` registry to `scripts/gh_json_fields.py`
- [x] Add `api_python_read_problems(tree)` with root filtering, chained/guarded `.get`, subscript and pair-constant derivation
- [x] Add ONE extra pass in `scan_file`, leaving every existing signature and the `--jq` path untouched
- [x] Pin the pre-change module as `tests/fixtures/gh_json_fields_base_1683.py` (blob `9e96236b2aaa20005b9d8fa1be8d91489218c284`) — no unconditional `git show origin/master` assertion
- [x] Add `tests/test_gh_json_fields.py::test_python_pick_rename_is_caught` with both `.get()` and `r["ref"]` plantings, RED on the pin
- [x] Add `::test_registered_reads_match_tree` (13-site equality, family subset, root-filter non-vacuity)
- [x] Add `::test_shipped_jq_shapes_still_green` (exit 0 / 0 findings, discovery 31/17/14, `--jq` families and `--json` sets unchanged)
- [x] Add `::test_fixed_origin_master_arm_is_green` (origin/master simulated to the fixed head; GREEN after merge)
- [x] Wire all four new tests into `main()` and prove RED on the pinned base (4 assertions) and GREEN on the head (152 passed / 0 failed)
- [x] Update the `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row with the slice-1 boundary and write `findings/1683.md` (13-site table, measurements, exclusions, owed row)
- [x] Run the fast offline checks: targeted module, `python3 scripts/gh_json_fields.py --scan`, `make lint`, `make architecture-check`, `make openspec-check` / index check
- [x] Push owner-identity branch `fix/gh-api-python-read-guard-1683`, open READY with `Closes #1683` in title AND body, record/archive the change and prove CI jobs on the head
