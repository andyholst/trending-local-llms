# Spec delta: readme-render (engine-guide-sync)

## ADDED Requirements

### Requirement: Reader-facing engine lists match the store on refresh
The validation stage SHALL verify that the README's `Inference engine / server guide` rows
and the `Which inference engine runs what` matrix columns match the store's engine registry
and the engines carrying measurements. A drift SHALL fail validation with the exact engine
names and the re-render command; the check SHALL be read-only and never mutate the store
(rule 3b).

#### Scenario: a refresh leaves a stale guide row
- **Given** an engine in the registry but absent from the README guide table
- **When** the check runs
- **Then** it exits non-zero, names that engine and suggests `--render-only`
- **Test:** tests/test_engine_guide_check.py

#### Scenario: a measured engine is missing from the matrix
- **Given** a measured engine absent from the matrix header columns
- **When** the check runs
- **Then** the finding names that engine; the shipped README passes with zero findings
- **Test:** tests/test_engine_guide_check.py