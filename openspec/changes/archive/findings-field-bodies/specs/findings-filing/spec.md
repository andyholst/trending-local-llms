# findings-filing

## ADDED Requirements

### Requirement: A finding's field keeps its continuation lines

A `- **Field:** …` marker in a finding MUST carry every line under it up to the next
marker, the next `## ` heading, or a blank line, and the filed issue body MUST contain
that text.

#### Scenario: a finding whose fields wrap onto the next lines

- **Given** a `findings.md` whose Evidence, Why and Done-when each continue on later lines
- **When** `scripts/file_findings.py --file` runs
- **Then** one `tech-debt` issue is created and its body carries every continuation fragment
- **Test:** tests/test_file_findings.py::test_a_multiline_field_keeps_its_continuation_lines

#### Scenario: an indented continuation is not read as a new field

- **Given** a continuation line indented under a marker, whose prose mentions `**Why:**`
- **When** the section is parsed
- **Then** the `Why` value is the real marker's text, not the prose inside the Evidence
- **Test:** tests/test_file_findings.py::test_a_multiline_field_keeps_its_continuation_lines
