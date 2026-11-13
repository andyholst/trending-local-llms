## ADDED Requirements

### Requirement: `write_raw_snapshot` never mutates the payload its caller passed

`write_raw_snapshot` SHALL build the snapshot from copies: the id/hf
normalisation, the formats rebuild and the refused-row drop SHALL land on the
written snapshot only, and every dict and list the CALLER passed SHALL be
unchanged, byte for byte, after the call.

#### Scenario: The caller's payload survives a rewriting write

- **Given** a payload whose model carries a contract-invalid id
  (`qwen3.8-27b-mlx_srv`) and a format whose `hf` is a full
  `https://huggingface.co/...` URL
- **When** `write_raw_snapshot(..., verify_hf=True)` writes the snapshot
- **Then** the caller's payload deep-equals its own pre-call copy, while the
  written snapshot carries the contract-normalised id and the collapsed
  `owner/repo` forms
- **Test:** tests/test_ingest_hf_verify.py::test_write_raw_never_mutates_the_caller_payload

#### Scenario: The refusal drop stays inside the snapshot

- **Given** a payload whose first model's `hf` a local HF stand-in answers `404`
- **When** the snapshot is written with `verify_hf=True`
- **Then** the written snapshot holds no row for that model (the loud
  `[write-raw] WARN:` fires), and the caller's payload still holds the row it
  passed, unmodified
- **Test:** tests/test_ingest_hf_verify.py::test_write_raw_never_mutates_the_caller_payload
