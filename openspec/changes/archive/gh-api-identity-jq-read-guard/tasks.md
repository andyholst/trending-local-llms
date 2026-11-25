# Tasks: gh-api-identity-jq-read-guard

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist + `.openspec.yaml`)
- [x] Fetch `origin/master` and re-measure on `6163bed6e4dc8f86d04d32fa24373213016a7912` (5 identity sites real, none covered by slice A; module blob `fd57014f869edee538387d5470ee23f218505e8d`)
- [x] Add the 5 identity `--jq .[]` records to the existing `API_PYTHON_READ_SITES` in `scripts/gh_json_fields.py` with measured file/line/caller/family/root/elements/readers/fields
- [x] Add `user` and `login` to the existing `API_PYTHON_FIELDS["issues/{}/comments"]` set only — no new family, extractor, signature or CLI flag
- [x] Set the `blocked` partitions (`issue` for `issue_thread`, `issue`/`issue_json` for `owed_rows_check`) and prove both halves are false-red-free with 0 findings on the unmodified tree
- [x] Pin the pre-slice-B module as `tests/fixtures/gh_json_fields_base_1711.py` (blob `fd57014f869edee538387d5470ee23f218505e8d`) — no unconditional `git show origin/master:` assertion
- [x] Add `::test_identity_jq_pick_rename_is_caught` (5 planted renames, RED on the pin, GREEN with file:line on the head)
- [x] Add `::test_all_18_registered_reads_match_tree` (18-site re-derivation, family subset, blocked partition load-bearing)
- [x] Add `::test_shipped_jq_projections_still_green` (exit 0 / 0 findings, 31/17/14, exactly 5 identity `.[]`)
- [x] Add `::test_fixed_origin_master_arm_is_green_1711` (origin/master simulated to the fixed head; both arms GREEN)
- [x] Wire all four new tests into `main()` and prove RED on the pinned base (12 failing checks) and GREEN on the head (235 passed / 0 failed)
- [x] Update the `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row and write `findings/1711.md` (site table, planted RED/GREEN file:lines, discovery totals, exclusions)
- [x] Run the fast offline checks: targeted module, `python3 scripts/gh_json_fields.py --scan`, `make lint`, architecture/index/openspec/findings checks
- [x] Push owner-identity branch `fix/gh-api-identity-jq-read-guard-1711`, open READY with `Closes #1711` in title AND body, record/archive the change and prove CI jobs on the head
