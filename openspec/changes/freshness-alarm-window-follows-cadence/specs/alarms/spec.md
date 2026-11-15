## ADDED Requirements

### Requirement: The freshness gate's window lives in the script, not in a workflow literal

`queued-alarm.yml`'s freshness-alarm step SHALL pass no `MAX_AGE_HOURS` override, and
the `_freshness-alarm` recipe SHALL forward `MAX_AGE_HOURS` only when supplied, so the
verdict window is `scripts/freshness_alarm.py`'s weekly `DEFAULT_MAX_AGE_HOURS` (170 h)
— one implementation, rule 6d. A weekly-cadence gap inside the default window SHALL pass;
an age past it SHALL fail naming the window.

#### Scenario: A normal weekly gap is inside the window

- **Given** a tree whose newest snapshot is 165 h old and a run that supplies no window override
- **When** `scripts/freshness_alarm.py` decides
- **Then** the alarm exits 0 and names the 170 h window as the one it used

- **Test:** tests/test_freshness_alarm.py::test_a_weekly_gap_is_inside_the_default_window

#### Scenario: A missed weekly slot goes red naming the window

- **Given** a tree whose newest snapshot is 180 h old
- **When** the alarm decides with no supplied override
- **Then** it exits 1 and the failure names the 170 h window and the age

- **Test:** tests/test_freshness_alarm.py::test_a_missed_weekly_slot_is_red_and_names_the_window

#### Scenario: No workflow or recipe carries a window literal

- **Given** the real `queued-alarm.yml` freshness step and the real `_freshness-alarm` recipe
- **When** the tests read them
- **Then** neither contains a `MAX_AGE_HOURS=` numeric literal, and the recipe forwards the variable only when supplied

- **Test:** tests/test_freshness_alarm.py::test_the_workflow_and_recipe_carry_no_window_literal
