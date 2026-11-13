# architecture-description

## ADDED Requirements

### Requirement: Every target-line matcher in the tree is the shared scan's view

A Makefile target-line matcher — the `name:` line test that decides which
target a line belongs to — exists in exactly one place,
`scripts/architecture_bot.py` (`_TARGET_LINE` / `_TARGET_SKIP`), and every
consumer reaches it through the module (`target_at_line`,
`_scan_target_names`, `make_targets`). A private regex copy is the #512 drift
class reintroduced at line level: two views of "what is a target" that can
disagree with no error raised (measured: the test copies count `.PHONY` lines
as targets — 145 in the real Makefile — while the shared scan skips them).

#### Scenario: a second target-line matcher literal appears outside the shared parser

- **Given** any tracked Python file under `scripts/` or `tests/`
- **When** it carries a target-line matcher regex (`:(?!=`) of its own
- **Then** the guard fails naming the file
- **Test:** tests/test_target_matchers_one_view.py::test_no_target_line_matcher_lives_outside_architecture_bot

#### Scenario: the --only attribution uses the shared line view

- **Given** a planted Makefile with a `.PHONY:` line and a `_validate-x` target whose recipe calls `scripts/validate.py --only …`
- **When** `architecture_check.stage_lists()` reads it
- **Then** the stage list is attributed to `_validate-x` (never to `.PHONY`) and the module carries no private `_ANY_TARGET`
- **Test:** tests/test_target_matchers_one_view.py::test_stage_lists_attributes_through_the_shared_view

#### Scenario: the test helper counts targets through the generator's parser

- **Given** the real Makefile and the real `architecture_bot` module
- **When** `tests/test_architecture_bot.py::_makefile_targets()` answers
- **Then** its set equals `architecture_bot.make_targets(ROOT)` exactly (`.PHONY` in neither)
- **Test:** tests/test_target_matchers_one_view.py::test_the_test_helper_is_the_shared_parser_not_a_copy
