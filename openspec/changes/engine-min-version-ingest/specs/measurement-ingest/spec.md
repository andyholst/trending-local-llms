# measurement-ingest

## ADDED Requirements

### Requirement: a captured engine-build sentence becomes the structured field at ingest

`scripts/update_trending.py` MUST, during `ingest_raw_snapshots`, fill the optional
measurement key `engine_min_version` from the free text the analysis already reads
(`quant` / `hardware` of the measurement merging into the store AND of the store row
it merges into) when that text matches `data_gap_analysis._ENGINE_MIN_TEXT` — the
ONE detector #876 widened. The value stored is the matched phrase VERBATIM; the
measurement's existing `source_post` is the citation, so every filled value traces
to a real post (rule 3, no fabrication). The fill prints loudly, naming how many
measurements gained the field.

#### Scenario: a build phrase in the text fills the field

- **Given** a captured measurement with no `engine_min_version` whose `hardware`
  reads `BigMoeOnEdge on stock llama.cpp (untouched upstream, submodule)`
- **When** `ingest_raw_snapshots` merges it into the store
- **Then** the stored measurement carries `engine_min_version` containing the
  matched phrase verbatim and its `source_post` unchanged
- **Test:** tests/test_engine_min_version_ingest.py::test_a_build_phrase_in_the_text_fills_the_field

#### Scenario: no build phrase, no field — the precision class stays exact

- **Given** a captured measurement whose text is `Q4_K_M (~14.6GB) on RTX 4090`
  (capacity and speed, no build claim)
- **When** the ingest fill runs
- **Then** the measurement has NO `engine_min_version` key and no other field changed
- **Test:** tests/test_engine_min_version_ingest.py::test_no_build_phrase_fills_nothing

#### Scenario: an existing value is never overwritten (rule 3b)

- **Given** a store measurement that already has `engine_min_version` and gains a
  new figure whose text also matches a build phrase
- **When** the fill runs on the merged row
- **Then** the existing value survives byte-identical and only a MISSING key is
  filled
- **Test:** tests/test_engine_min_version_ingest.py::test_an_existing_value_is_never_overwritten

#### Scenario: the detector has exactly one implementation (rule 6d)

- **Given** the ingest seam
- **When** the suite inspects `update_trending`
- **Then** it matches with the SAME compiled pattern object imported from
  `data_gap_analysis`, and `update_trending` defines no own build-phrase regex
- **Test:** tests/test_engine_min_version_ingest.py::test_the_build_detector_has_one_implementation

#### Scenario: the report's unstructured list shrinks when ingest fills

- **Given** a fixture store whose models state builds only in prose (the #877 class)
- **When** the fill runs and `data_gap_analysis.analyse` re-runs on the result
- **Then** `unstructured:engine_min_version` is strictly smaller and the filled
  models are no longer listed as ingest gaps
- **Test:** tests/test_engine_min_version_ingest.py::test_the_unstructured_list_shrinks_after_the_fill
