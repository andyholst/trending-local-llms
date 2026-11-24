## ADDED Requirements

### Requirement: A findings file carrying both a finding section and a `- none` line is refused

`scripts/file_findings.py::parse()` SHALL refuse a findings file that contains at
least one `## <title>` section AND a line matching `^\s*[-*]\s+none\s*$`. The
returned error SHALL name both conflicting shapes and state that the analysis would
otherwise be silently dropped. A `- none`-only file SHALL remain a valid empty
result, and a sections-only file SHALL parse exactly as before.

#### Scenario: A mixed file is refused, not read as empty

- **Given** a findings file carrying one complete `## <title>` finding (Evidence /
  Why / Done when) followed by a `- none` line
- **When** `parse()` reads it, or `python3 scripts/file_findings.py --check --path
  <file>` runs on it
- **Then** `parse()` returns an error naming the finding-section shape and the
  `- none` shape, and `--check` exits non-zero naming the file
- **Test:** tests/test_file_findings.py::test_a_mixed_finding_and_none_file_is_refused

#### Scenario: A `- none`-only file stays a valid empty result

- **Given** a findings file whose body is `# Findings` plus a single `- none` line
- **When** `--check` runs on it
- **Then** it exits zero and reports `0 finding(s)`, byte-identical to the old
  behaviour
- **Test:** tests/test_file_findings.py::test_none_is_a_valid_empty_analysis

#### Scenario: A sections-only file is unchanged

- **Given** a findings file with one complete finding and no `- none` line
- **When** `--check` runs on it
- **Then** it exits zero and reports `1 finding(s)`
- **Test:** tests/test_file_findings.py::test_a_sections_only_file_still_parses

#### Scenario: The shipped mixed files report their findings

- **Given** the repository's `findings/1586.md` (three findings) and
  `findings/1612.md` (one finding)
- **When** `python3 scripts/file_findings.py --check --path <file>` runs on each
- **Then** each exits zero and reports its real finding count (`3` and `1`), because
  the stray `- none` line is gone
- **Test:** tests/test_file_findings.py::test_the_shipped_findings_files_are_not_mixed
