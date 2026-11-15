# engine-min-version-detection

## ADDED Requirements

### Requirement: A `<version>` is refused as an engine build when a throughput unit follows it

`_ENGINE_MIN_TEXT` MUST NOT classify a `<version>` as an `engine_min_version`
build claim when the version is immediately followed by a throughput unit
(`tokens/s`, `tok/s`, or `TPS`/`tps`) near an engine name — the number is a t/s
speed, not a build, and structuring it would store a speed as a version (rule 2
fabrication). The post states no build, so the model stays an ACQUISITION gap
(`not_captured`), never "stated in prose only, an ingest job".

#### Scenario: a t/s speed after the engine is not a build claim

- **Given** a captured post whose text states `llama.cpp 306.9 tokens/s on the
  identical GGUF` (the empirical `qwen2.5-0.5b` capture) and no other build phrase
- **When** the data-gap analysis runs that capture against the store
- **Then** the model is NOT in `unstructured["engine_min_version"]` and IS in
  `not_captured["engine_min_version"]`
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_refuses_a_throughput_after_the_engine

#### Scenario: a tok/s speed after the engine is refused too

- **Given** a captured text `llama.cpp 44.8 tok/s on the identical GGUF` (the
  empirical `gemma-4-e4b` capture, `tok/s` spelling)
- **When** the engine-build detector scans that text
- **Then** it does not match (no build claim), and the row reclassifies as an
  acquisition gap
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_refuses_a_throughput_after_the_engine

#### Scenario: an uppercase TPS after the engine is refused too

- **Given** a captured text `llama.cpp 150 TPS on the identical GGUF`
- **When** the engine-build detector scans that text
- **Then** it does not match (a rate, never a build)
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_refuses_a_throughput_after_the_engine

### Requirement: Genuine build phrasings are still captured

The throughput refusal MUST be precise (#214/#213): a `<version>` that is a real
engine build — including one that merely precedes a later, separate speed — MUST
still classify the post as stating a build, and the classes MUST stay a disjoint
partition of the missing set.

#### Scenario: a real build before a later speed is still an ingest job

- **Given** a captured text `llama.cpp build 2.1, measured 306.9 tokens/s`
- **When** the engine-build detector scans that text
- **Then** it DOES match (the `2.1` is a build, the `306.9` is a separate later
  speed), and the model is in `unstructured["engine_min_version"]`
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_refuses_a_throughput_after_the_engine

#### Scenario: the classes still partition the missing set

- **Given** the store analysed against captures that include the throughput
  over-matches and a genuine build, over `engine_min_version`
- **When** the four prose/capture classes are collected
- **Then** every missing model appears in exactly one class and the partition
  equals `missing["engine_min_version"]`
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_refuses_a_throughput_after_the_engine
