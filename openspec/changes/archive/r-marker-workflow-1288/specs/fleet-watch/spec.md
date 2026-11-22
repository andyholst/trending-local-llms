## ADDED Requirements

### Requirement: The CI marker names the workflow that produced it

The monitor SHALL add an optional, colon-safe workflow-name token to an `R:`
marker when the run row provides `name`, so a reader can distinguish a
`guard`/`closure`-only `success` from a full validation without a second call.
The existing `id`, `status` and `conclusion` fields SHALL be unchanged, and a run
row with no usable name SHALL emit the original marker.

#### Scenario: A guard/closure success is distinguishable from a full validation

- **Given** two completed `success` run rows on the same head, one named
  `pr-closure` and one named `qa-validate`
- **When** the monitor diffs a snapshot whose run states changed
- **Then** it emits two distinct `R:` markers whose fourth field is the workflow
  name, and neither full-validation conclusion is claimed from the bare conclusion
- **Test:** tests/test_watch_monitor.py::test_r_marker_carries_workflow_name

#### Scenario: The workflow token cannot break the marker shape

- **Given** a workflow name containing a colon and a newline
- **When** the monitor builds the `R:` marker
- **Then** the token is colon-free and single-line, leaving exactly one field per
  `:`, and a nameless run still emits the three-field marker
- **Test:** tests/test_watch_monitor.py::test_r_marker_carries_workflow_name
