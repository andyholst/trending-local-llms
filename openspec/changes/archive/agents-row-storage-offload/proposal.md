# The §8 row the storage_offload guards owed

**Issue:** [#369](https://github.com/andyholst/trending-local-llms/issues/369)
**Capability:** `agents-guard-registry`

## Why

`#364` (PR #366) closed the ranked `storage_offload` dimension with two guards —
`test_storage_offload_backfill_traces_to_the_captured_source_text` and
`test_storage_offload_coverage_can_never_shrink` — and rule 6c required their §8 row in the same
change. The row could not be written: `AGENTS.md` is a protected file and the approval prompt does
not return in a headless bot run ("Silence is not consent", #310), so the guards shipped registered
in `make test` and **undiscoverable from the rulebook**.

The issue's own body is also damaged — `issue.md` lines 5-7 end mid-clause — so the row's content is
**derived** from the change that added the guards (`openspec/changes/data-gap-storage-offload`,
tasks 4/5), never invented.

## What Changes

- **`AGENTS.md` §8** — one row naming both guards, what they catch (a structured value with no
  captured source text behind it; a closed dimension silently shrinking back to missing), the module
  they live in, and the change that added them (`#364`, PR #366). It sits directly below the
  `engine_min_version` rows, which is the family it belongs to.
- **`tests/test_agents_rows.py`** — `test_the_storage_offload_row_is_written` pins the row: both
  guard names, the module, "no captured"/"invented", the coverage floor, the citing issue and PR, and
  its position beside the `#163` rows. Without it the row could be deleted and the rulebook would go
  quiet again.

## Impact

The last known owed §8 row of its class lands. The other four (#310/#391/#400) were already pinned by
the same test module; a future change that ships a guard without its row still reds only its own
`findings.md` ledger, but a row that EXISTS can no longer vanish.

## Not covered (out of scope)

- The remaining owed rows from this session's changes (the working-file list, the marker registry,
  the search-tool pin, the adopt refusals) are recorded in their own `findings.md` files; each needs
  its own change and its own approval, and folding them in here would make one PR close ten issues.
