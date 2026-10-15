# data-gap-backfill

## ADDED Requirements

### Requirement: A stated requirement dimension is stored, not left in prose

A gap dimension the contracts declare OPTIONAL — `engine_min_version` first —
MUST be backfilled into the model-level structured field from the source post's
own words whenever the post states it, additively: no existing key is removed or
renamed and no existing value is shrunk. A model whose captured text states
nothing for the dimension MUST be left unset, so the gap stays reported instead
of being closed with an invented value.

WHEN a source post states the engine build or the required flags a figure
reproduces on,
THEN the model carries that statement as a structured `engine_min_version`.

#### Scenario: a stated engine build becomes a structured value

- **Given** a model whose captured source text names the build it reproduces on
  (e.g. "Vulkan (llama.cpp b9292), MTP speculative decode") and which has no
  `engine_min_version`
- **When** the store is backfilled
- **Then** the model carries `engine_min_version` naming that build and flags, and no other key of the model is changed
- **Test:** `tests/test_data_gap_analysis.py::test_engine_min_version_coverage_can_never_shrink`

#### Scenario: a model whose post states nothing is left unset

- **Given** a model whose captured text names only an engine with no build, version or flag
- **When** the store is backfilled
- **Then** the model still has no `engine_min_version` — the gap stays reported rather than closed with an invented value
- **Test:** `tests/test_data_gap_analysis.py::test_engine_min_version_coverage_can_never_shrink`

### Requirement: Every structured value traces to the captured source text

A model-level `engine_min_version` MUST be evidenced by the model's own captured
source text in `data/raw/*.json` — the snapshot of a real `…/status/<id>` post.
Every version-like token of the value MUST appear in that text, and at least one
distinctive token of it MUST appear; a value that no captured post supports is a
fabrication and MUST fail the suite.

WHEN a structured dimension value is written into the store,
THEN the suite proves the post behind it says the same thing.

#### Scenario: the value is present in the captured text of a real post

- **Given** the real store and the raw search snapshots
- **When** the traceability guard runs
- **Then** every model carrying `engine_min_version` has all its version-like tokens, and at least one distinctive token, present in the text captured for that model, and a real post URL on at least one of its measurements
- **Test:** `tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text`

#### Scenario: an invented value fails the guard

- **Given** a store whose model carries an `engine_min_version` no captured snapshot mentions
- **When** the traceability guard runs
- **Then** it fails, naming the model
- **Test:** `tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text`

### Requirement: The closed gap cannot silently reopen

The dimension's coverage MUST be asserted against a floor, so a change that drops
the backfilled values (or a regeneration that loses them) turns the suite red.

WHEN the store is regenerated without the backfill,
THEN the coverage guard fails.

#### Scenario: coverage floor holds on the real store

- **Given** the real store after this change
- **When** the coverage guard runs
- **Then** at least 25 models carry a structured `engine_min_version` and the analysis reports fewer models missing it than the 29/30 the filed issue recorded
- **Test:** `tests/test_data_gap_analysis.py::test_engine_min_version_coverage_can_never_shrink`
