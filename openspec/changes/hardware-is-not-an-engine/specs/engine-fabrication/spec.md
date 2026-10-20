# engine-fabrication

## ADDED Requirements

### Requirement: A hardware name is never an engine

A measurement whose `engine` is absent from the engines registry and whose name carries a
CPU/GPU product token MUST be refused at ingest, exactly like a quantization token, and
the refusal MUST name the token it saw.

#### Scenario: the measured hardware shape

- **Given** a raw measurement on `bonsai-2-9b` with `engine: "Bonsai Oryon"` (Oryon is Qualcomm's CPU core)
- **When** the engine name is judged
- **Then** it is refused as hardware, so the refresh PR cannot go red on it
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest

### Requirement: The boundary holds for real engine names

An engine whose name merely CONTAINS the letters of a hardware token (`strixite`) or a
quant-looking fragment (`ExLlamaV3`) MUST NOT be refused when it is not in the registry.

#### Scenario: strixite and ExLlamaV3

- **Given** the engine names `strixite`, `ExLlamaV3`, `MLX`, `mlx-serve`, `llama.cpp`
- **When** each is judged against an empty registry
- **Then** none is refused
- **Test:** tests/test_engine_registry.py::test_fabricated_engine_refused_at_ingest
