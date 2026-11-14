# Proposal: declared-est-reask-pipeline

Issue: #936

## Why

Rule 2 allows a projection into the store precisely because it is **marked**:
`(est)` / `(estimated)`. The validator now refuses an *untraceable* composite
that splices the marker in (issue #933 landed `_DECLARED_ESTIMATE` there), but
the analysis side — `scripts/data_gap_analysis.py`, the thing that decides what
the next refresh should *ask for* — had no idea the marker existed. Its classes
are `missing` / `unstructured` / `not_captured` / `untraceable`, and a
`(est)`-marked footprint value fell into none of them:

```python
if value in (None, "", [], {}):   # an "(est)" string is not missing …
...unstructured detector           # … and its detector never reads the marker
```

So a declared estimate was invisible to the acquisition chain. The refresh
already derives a footprint query per trending model (rule 6o:
`footprint_query()` asks for `vram ram context weights offload engine version`),
yet nothing ever told it *which* model+field entries are projections that such a
query could replace with a measured post. Rule 2's honest placeholders therefore
shipped as card-table advice forever — never re-asked, never upgraded.

## What Changes

- **`scripts/declared_estimate.py`** — the ONE declared-estimate detector
  (rule 6d): `DECLARED_ESTIMATE` (the marker regex), `FOOTPRINT_FIELDS` (byte-
  identical order to the analysis's `DIMENSIONS`), `has_declared_estimate()`,
  and `footprint_estimates(models)` → `field -> ["model/engine:field=value", …]`
  for measurement-level AND model-row values. Stdlib-only, because
  `make data-gap-issue` runs the filer on host python that has no `jsonschema`
  — importing `validate` there is an ImportError, so the detector lives in a
  module both sides can import.
- **`data_gap_analysis.py`**: imports the module (never its own regex); a new
  report key `declared_estimates`; a new finding line naming the re-askable
  values; a signature entry **once per field** (`reask_estimate:<field>` — the
  #472 stability lesson: per-model detail lives in the body, the signature
  stays stable while the class persists); new sections in `render()` and in
  `issue_body()` that name every model+field so the next search can be aimed
  at exactly them.
- **Tests** in `tests/test_data_gap_analysis.py`:
  `test_declared_estimates_surface_as_a_reaskable_class` (both marker spellings,
  both value levels, measured values excluded, signature once-per-field, report
  and issue body name each model+field, empty class reports `none` and adds no
  signature entry) and `test_the_declared_estimate_detector_is_one_detector`
  (field set IS `DIMENSIONS`, the analysis carries no marker regex of its own).

## Impact

`scripts/declared_estimate.py` (new), `scripts/data_gap_analysis.py`,
`tests/test_data_gap_analysis.py`, `ARCHITECTURE.md` §6 row, `AGENTS.md` §8 row,
this OpenSpec change and the regenerated `OPENSPEC.md`. No stage, target, job
or image changes. On the real store the new section names the `(est)` footprint
values the gap-issue then lists for re-asking.

## Not covered

- **Replacing the estimates with measured figures.** This change makes them
  visible and re-askable; each replacement is a separate data update traced to
  a post (rule 2), and additive-only (rule 3b) forbids deleting the estimate.
- **`validate.py` importing this module instead of keeping its own `_DECLARED_ESTIMATE`
  literal.** That collapse is the rule-6d endgame, but `validate.py`'s copy was
  added by issue #933, which must merge into `master` before this branch can
  edit it — see the blocked task.
