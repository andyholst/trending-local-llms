# engine-fabrication

## ADDED Requirements

### Requirement: A fabricated engine never reaches the store

A measurement whose `engine` is absent from the engines registry and whose name is
provably derived from the model or the quantization MUST be refused at ingest, and
the refusal MUST be loud and name the model, the engine and the source post.

#### Scenario: the measured row

- **Given** a raw snapshot carrying `engine: "FP4-Local"` for `qwen3.8-flash-next-125b`
- **When** the snapshot is ingested
- **Then** that measurement does not enter the store, the model's other measurements survive, and a `[ingest] REFUSED fabricated engine` line names the post
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest

#### Scenario: the two measured spellings

- **Given** the engine names `FP4-Local` (2026-10-20) and `NVIDIA FP4-Local` (#378, 2026-10-19)
- **When** each is judged
- **Then** both are refused, and the reason names the quantization token they carry
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest

#### Scenario: an engine that appears in the model name

- **Given** `WebLLM`, absent from the registry and also a substring of `Llama-3.1-8B (WebLLM)`
- **When** it is judged
- **Then** it is NOT refused — a model-name substring is not proof, and refusing it breaks a real engine
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest

### Requirement: A genuine new engine is never swallowed

An engine that is simply not registered yet MUST NOT be refused: it keeps reaching
the store, and `make validate` keeps failing for a human, because the registry — not
the ingest — decides what is an engine.

#### Scenario: an unregistered but plausible engine

- **Given** the engine name `SomeRealServe`, absent from the registry and carrying no repo
- **When** it is judged
- **Then** it is not refused, so validation still reports it for a human
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest

#### Scenario: a registered engine

- **Given** `vLLM`, present in the engines registry
- **When** it is judged
- **Then** it is never refused
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest
