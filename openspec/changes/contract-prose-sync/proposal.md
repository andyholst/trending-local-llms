# Proposal: contract-prose-sync

Issue: #1394

## Why

`data/MODEL_CONTRACT.md` summarises `data/model_contract.json` and has no owner, so it drifts silently. Measured on `da86387c` (design on #691): the field table carried **21 rows** while the schema declared **23** model properties (`engine_aliases`, `measurement_model_aliases` had no row), and the `hf`/`engines` rows said required while the schema does not require them. A reader could not tell the shipped store shape from the prose — the same class as #1390.

This is **slice A of #691** (the machine-checkable half). Slices B (the store architecture page) and C (the `tll-docs` lane) are separate issues.

## What Changes

- New `scripts/check_contract_prose.py` — the ONE seam. It parses the pipe-table rows of `data/MODEL_CONTRACT.md` (`| \`field\` | yes/no | … |`) and compares them to `data/model_contract.json`'s `properties.models.items`: every schema property MUST have a row; every Required cell MUST equal membership in `required`; unknown rows FAIL. Presence and required-ness are hard fail; the Meaning cell is prose and is never parsed.
- Register `check_contract_prose()` in `scripts/validate.py` under a NEW stage `docs`, added to `_validate`'s all-run list AND selected by the existing `_validate-schema` target (`--only schema,docs`). No new make target (rule 6d), no job, no image.
- New `tests/test_contract_prose.py` — real files, no mocks (rule 6m).
- Fix the two known deltas additively (never delete): add rows for `engine_aliases` + `measurement_model_aliases`; correct the `hf`/`engines` required cells to the schema's actual value. Same change (rule 6b).
- `ARCHITECTURE.md`: §2 bullet naming the script, §6 row, §8 row (rule 6h).

## Impact

No data format, contract, schema, store value, README, workflow or image change. `make validate` and `make validate-schema` gain the `docs` stage; every existing gate stays green. The check is read-only (rule 3b) and names both sides of every drift finding.

## Not covered

`data/models.json`, the README, any contract JSON, a workflow, a cron, a profile home, slices B/C, and prose wording in the Meaning column.
