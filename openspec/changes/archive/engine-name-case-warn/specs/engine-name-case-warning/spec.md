## ADDED Requirements

### Requirement: The raw writer WARNs on an engine-name case slip without renaming

`write_raw_snapshot` SHALL, when a measurement's `engine` name is absent from
the engines registry and its lower-cased spelling matches a registered name,
print one loud `[write-raw] WARN:` naming the backend, the model id, the
written spelling and the registered spelling. It SHALL NOT rename the written
name and SHALL NOT refuse the measurement. The check is local and SHALL run
regardless of `verify_hf`, making no request. An exact registered name and a
genuinely new engine name (no case-insensitive match) SHALL print nothing.

#### Scenario: A case-only slip against a registered engine warns

- **Given** a payload whose model carries an engine measurement whose name
  differs from a name in the real registry by case alone (`ExLlamaV3`
  swap-cased)
- **When** `write_raw_snapshot(..., verify_hf=False)` writes the snapshot
- **Then** the log names the model id, the written spelling and the registered
  spelling, and the written snapshot holds the engine name unchanged
- **Test:** tests/test_ingest_hf_verify.py::test_write_raw_warns_on_engine_name_case_slip

#### Scenario: The exact registered name is silent

- **Given** a measurement whose engine name matches a registered name exactly
- **When** the snapshot is written
- **Then** no WARN names that model and the measurement is written unchanged
- **Test:** tests/test_ingest_hf_verify.py::test_write_raw_warns_on_engine_name_case_slip

#### Scenario: A genuinely new engine is silent and stays for auto-register

- **Given** a measurement whose engine name matches no registered name under
  any casing
- **When** the snapshot is written
- **Then** nothing is printed for it and the measurement survives for the
  auto-register path (`make engine-check`, rule 6)
- **Test:** tests/test_ingest_hf_verify.py::test_write_raw_warns_on_engine_name_case_slip

#### Scenario: The case check costs no request

- **Given** a payload with a case slip written with `verify_hf=False`
- **When** the writer runs
- **Then** the HF seam made zero requests and the WARN still fired
- **Test:** tests/test_ingest_hf_verify.py::test_write_raw_warns_on_engine_name_case_slip
