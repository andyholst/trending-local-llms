# measurement-attribution

## ADDED Requirements

### Requirement: A shipped joint figure is documented as data on its row

A shipped measurement that legitimately compares the row's model against another
stored model MUST carry that exception as DATA in the row's
`measurement_model_aliases` (every counterpart a model id in the store), so the
report-only attribution scan no longer reports it; a misattribution with no honest
exception MUST stay reported until the owner rules on it (rule 3b — a removal is a
human decision, never an agent's).

#### Scenario: the shipped joint figure is exempted by its data exception

- **Given** the shipped store's `qwen3.6-35b-a3b` row, whose vLLM 309 t/s post is
  a joint benchmark naming `Qwen3.8-27B`, carrying
  `measurement_model_aliases: ["qwen3.8-27b"]`
- **When** `misattributed_measurements` runs over the shipped store
- **Then** the 35B-A3B row is not reported, the alias passes
  `check_measurement_alias_map`, and the counterpart `qwen3.8-27b` is a model id
  in the store
- **Test:** tests/test_measurement_attribution.py::test_the_shipped_joint_figure_is_documented_as_data

#### Scenario: the undecided misattribution is still reported

- **Given** the shipped store's `qwen-3.6-27b` row whose llama.cpp 140 t/s
  measurement names Qwen 3.5 35B and has no honest alias
- **When** the attribution scan runs over the shipped store
- **Then** the row is still reported (no silent laundering, no agent-side removal)
- **Test:** tests/test_measurement_attribution.py::test_the_shipped_store_reports_the_known_row
