## ADDED Requirements

### Requirement: Declared-estimate engine builds are named, not silently counted

The data-stage report-only class SHALL name every model-level `engine_min_version` value
that carries the canonical `(est)` marker (rule 2), by model id, field name and stored
value, as a rule-3b human-decision candidate. Listing SHALL be report-only (never a gate
failure), SHALL NOT modify, delete or shrink any stored value (rule 3b), and SHALL NOT make
the human rule-3b decision. A value without the `(est)` marker SHALL NOT appear in this
list by virtue of this requirement.

#### Scenario: A stored (est) toolchain compound is surfaced by name

- **Given** a model whose `engine_min_version` is
  `SonicBoom 0.0.3 (C++/CUDA, MLIR compiler, zero Python) (est)` and whose capture states
  no such build
- **When** the data-stage `check_model_footprint_copy` runs on that store
- **Then** the report names the model `gemma-4-e4b`, the field `engine_min_version` and the
  stored value; no gate failure is added; and the stored value is unchanged
- **Test:** tests/test_model_footprint_copy.py::test_declared_estimate_engine_build_is_named_in_report
