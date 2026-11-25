# Tasks: gh-json-fields-scope-boundary

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist + `.openspec.yaml`)
- [x] State the BOUNDARY in the `scripts/gh_json_fields.py` module docstring: only `--jq`/`-q` projections are validated, Python-side `.get()` field picks are OUT OF SCOPE, with the 32/18/2 counts and the re-derivation command
- [x] Narrow the `api_jq_requests` docstring exemption to the ABSENCE OF A PROJECTION and cite #1675
- [x] Update the inline exemption comment to `# no --jq/-q projection: exempt (Python-side field picks are out of scope, #1675)`
- [x] Add `PYTHON_GET_FIELDS_OUT_OF_SCOPE = True` and `UNVALIDATED_PYTHON_API_READ_SITES = 18`
- [x] Land the matching `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row clause
- [x] Add `tests/test_gh_json_fields.py::test_the_scope_claim_matches_the_tree` plus its one `main()` call, RED-first on `git show origin/master:scripts/gh_json_fields.py`
- [x] Prove non-vacuity: a scratch tree whose only `gh api` call picks a field in Python scans GREEN, and the shipped discovery totals stay 31/17/14 with 5 identity `.[]` projections
- [x] Run the fast offline checks: targeted module, `python3 scripts/gh_json_fields.py --scan`, `make lint`, `make architecture-check`, `make openspec-index-check`
- [x] Write `findings/1675.md`; regenerate `OPENSPEC.md`; push READY with `Closes #1675` in BOTH title and body and record/archive this change on that branch
