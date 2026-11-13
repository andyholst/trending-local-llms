# measurement-ingest

## ADDED Requirements

### Requirement: a captured engine-build sentence becomes the structured field at ingest

`scripts/update_trending.py` MUST, during `ingest_raw_snapshots`, fill the optional
measurement key `engine_min_version` on every incoming raw measurement whose OWN
text (`quant` / `hardware` — the capturing post's record; the model's `why` is agent
prose and NEVER fills a value, rule #470) matches `data_gap_analysis._ENGINE_MIN_TEXT`
— the ONE detector #876 widened. The value stored is the matched phrase VERBATIM; the
measurement's existing `source_post` is the citation, so every filled value traces to
a real post (rule 3, no fabrication). `merge_engines`' existing same-post dimension
fill then carries the value onto the store measurement the same post produced.

#### Scenario: a build phrase in the raw measurement text fills the field

- **Given** a captured raw measurement with no `engine_min_version` whose `hardware`
  reads `BigMoeOnEdge on stock llama.cpp (untouched upstream, submodule)` with a
  real `source_post`
- **When** `ingest_raw_snapshots` ingests its snapshot
- **Then** the store measurement that post produced carries `engine_min_version`
  containing the matched phrase verbatim and its `source_post` unchanged
- **Test:** tests/test_engine_min_version_ingest.py::test_a_build_phrase_in_the_captured_text_fills_the_field

#### Scenario: no build phrase, no field — the precision class stays exact

- **Given** a captured raw measurement whose text is `Q4_K_M (~14.6GB) on RTX 4090`
  (capacity and speed, no build claim)
- **When** the ingest fill runs
- **Then** the measurement has NO `engine_min_version` key and no other field changed
- **Test:** tests/test_engine_min_version_ingest.py::test_no_build_phrase_fills_nothing

#### Scenario: an existing value is never overwritten (rule 3b)

- **Given** a raw measurement that already has `engine_min_version` AND whose text
  also matches a build phrase
- **When** the fill runs
- **Then** the existing value survives byte-identical and only a MISSING key is
  ever written
- **Test:** tests/test_engine_min_version_ingest.py::test_an_existing_value_is_never_overwritten

#### Scenario: the detector has exactly one implementation (rule 6d)

- **Given** the ingest seam
- **When** the suite inspects `update_trending`
- **Then** it matches with the SAME compiled pattern object imported from
  `data_gap_analysis`, and `update_trending` defines no own build-phrase regex
- **Test:** tests/test_engine_min_version_ingest.py::test_the_build_detector_has_one_implementation

#### Scenario: the report's ingest class closes when the seam runs

- **Given** a fixture store + fixture raw snapshot where the build sentence lives
  only in the captured post text (the `captured:` class — an INGEST job the report
  already names)
- **When** `ingest_raw_snapshots` merges it and `data_gap_analysis.analyse` re-runs
- **Then** the model leaves `captured:engine_min_version` and its measurement holds
  the structured value
- **Test:** tests/test_engine_min_version_ingest.py::test_the_captured_class_closes_after_the_fill

#### Scenario: `why` prose never fills a value

- **Given** a raw model whose `why` states `0.0.3 (C++/CUDA build)` but whose
  measurements state no build phrase
- **When** the fill runs
- **Then** no `engine_min_version` is written anywhere (agent prose is not evidence,
  #470)
- **Test:** tests/test_engine_min_version_ingest.py::test_model_why_prose_never_fills_a_value
