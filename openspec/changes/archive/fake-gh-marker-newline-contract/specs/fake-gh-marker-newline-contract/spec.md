# fake-gh-marker-newline-contract

## ADDED Requirements

### Requirement: The gap-issue body ends with a trailing newline

The data-gap filer's emitted issue body MUST end with a trailing newline, so
the invisible `data-gap-signature` dedup marker (the body's final line) is a
complete, newline-terminated line that a line-by-line consumer can always read.
The consumer side (`_GH_STUB` / `_GH_STUB_LABELS`) relies on this contract and
MUST document it, so a change to either side alone — a renderer that trims the
newline, or a stub that stops consuming one — cannot silently drop the last
entry's dedup marker (the #996 re-file class, issue #1002).

#### Scenario: the filer body ends with a newline and the marker is preserved

- **Given** `scripts/data_gap_analysis.py::issue_body` composing a body whose
  final element is the `data-gap-signature` marker line
- **When** the returned body is examined and then fed to the `issue create`
  stub exactly as `file_issue` pipes it
- **Then** the body string ends with `\n`, the final marker line is present and
  complete, and a shared newline-assertion test asserts both so neither the
  renderer nor the stub can regress alone
- **Test:** tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline

#### Scenario: the stubs document the newline contract they rely on

- **Given** the fake `gh` `issue create` stubs in `tests/test_data_gap_analysis.py`
- **When** a reader opens either stub
- **Then** its `issue create` arm carries a comment stating that the product
  body ends with a trailing newline and that the stub consumes it as such
- **Test:** tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline
