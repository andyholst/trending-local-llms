## ADDED Requirements

### Requirement: The validate-job gate extractor reads shell terminators and ignores prose

`scripts/master_alarm.py::validate_gates_from_trees` SHALL recognise a
`make <target>` terminated by `;`, `|`, `&`, `)`, a backtick, a quote,
whitespace or end-of-line, and SHALL NOT manufacture a gate from prose: a `#`
comment line, a line whose command word is `echo`/`printf`/`say`/`warn`/
`annotate`, or a `make <target>` inside a quoted span contributes nothing.

#### Scenario: A gate terminated by a shell operator is extracted

- **Given** a validate-job text containing `if ! make openspec-index-check; then`
  and `make image-ensure | tee log`
- **When** `validate_gates_from_trees` reads it
- **Then** both `openspec-index-check` and `image-ensure` are extracted
- **Test:** tests/test_master_alarm.py::test_every_validate_gate_is_on_a_list

#### Scenario: A planted `make <newgate>;` is an uncovered gate

- **Given** a validate-job text with a planted `run: make brand-new-gate;` that
  `GATES` does not name
- **When** `unchecked_gates` reads it
- **Then** `brand-new-gate` is reported as uncovered (so the registry test reds
  until `GATES` names it)
- **Test:** tests/test_master_alarm.py::test_every_validate_gate_is_on_a_list

#### Scenario: A prose `make <target>` literal is not a gate

- **Given** a validate-job text carrying
  `echo "[merge-tree-index] Run 'make openspec-index' and rebase on current master."`
  and a `#` comment naming `` `make openspec-check` ``
- **When** `validate_gates_from_trees` reads it
- **Then** neither `openspec-index` nor the comment's `openspec-check` is
  extracted as a gate
- **Test:** tests/test_master_alarm.py::test_every_validate_gate_is_on_a_list
