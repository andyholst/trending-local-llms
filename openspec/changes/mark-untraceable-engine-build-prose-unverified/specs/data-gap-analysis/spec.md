# data-gap-analysis spec delta

## ADDED Requirements

### Requirement: Engine-build claims no captured post supports are declared unverified on the model row

When a model row states an engine **build** in free text and no captured post supports it,
the store must NOT leave the claim as unattributable prose: the row carries a model-level
`engine_min_version` distilled from the row's own wording and carrying the declared-estimate
marker (`(est)`, rule 2), which the analysis lists as a re-askable declared estimate. The
backfill evidence guard remains fully in force for every **unmarked** value: only the marker
exempts a value from the captured-text and post-URL evidence checks.

#### Scenario: The shipped store states no untraceable engine build

- Given the shipped `data/models.json` and the captured `data/raw` snapshots
- When `data_gap_analysis.analyse()` classifies stated figures
- Then the untraceable `engine_min_version` class is empty, each of the five flagged rows
  (`bonsai-2-9b-apple-silicon-yukon`, `qwen2.5-0.5b`, `qwen3-8-flash-next-125b`,
  `gemma-4-e4b`, `qwen3.8-27b-r9700-vllm-dflash2-w4a16`) carries a model-level
  `engine_min_version` marked `(est)`, and the report's declared estimates name them
- **Test:** tests/test_data_gap_analysis.py::test_untraceable_engine_build_prose_is_declared_unverified_in_the_store

#### Scenario: The backfill guard exempts only the marker

- Given a structured model-level `engine_min_version` value
- When the #163 backfill guard checks captured-text evidence and a real `…/status/<id>` post
- Then a value carrying the `(est)` marker passes without either (a declared estimate claims
  no fact), and an unmarked invented value fails both
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text
