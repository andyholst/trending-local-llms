# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit, and `triage.md` is `implement`
- [x] 2. `scripts/validate.py`: `source_post_figure_flags(store, raw_dir)` builds a source_post ->
      captured-text index from `data/raw/*.json` (the captured measurement's `quant`/`hardware`
      free text plus its structured footprint fields), normalises stored footprint values
      (whitespace/comma-insensitive + figure tokens), and returns one flag per stored footprint
      value that appears in NEITHER the capture's fields NOR the post text
- [x] 3. `check_source_post_readback(store)` is a report-only scan registered under the existing
      `data` stage (`add("source-post readback (report only)", "data", …)`), so
      `make validate` runs it and rule 6d's wiring test stays green
- [x] 4. `tests/test_source_post_readback.py` (new) exercises the REAL read against a real temp
      raw snapshot directory — a stored value the capture states is kept, one the capture
      nowhere states is flagged, a captured structured field confirms a value, an uncaptured
      post is skipped, and the scan never fails on the shipped store (no mock of business logic)
- [x] 5. AGENTS.md §8 gains a row for the scan and its test module
- [x] 6. Gates green: `scripts/run_tests.sh`, `scripts/validate.py` (data-stage python
      equivalent of `make validate` minus the network `links` stage run in this agent container
      where docker is absent), `scripts/lint_*`, `scripts/openspec_index.py --write` +
      `--check`, `scripts/check_openspec_tasks.py`
