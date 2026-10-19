# secret-output-guard

## ADDED Requirements

### Requirement: The guard scans every text file, whatever its suffix

A committed credential-shaped literal MUST be reported from any text file in the
repository — `.txt`, `.json`, `.toml`, `.md`, extension-less — not only from the suffixes
that happened to be whitelisted. Binary files (a NUL byte in the first 8000) and empty
files are never findings.

#### Scenario: a value committed into a data file

- **Given** a repository tree with `notes.txt` and `config/app.toml` each carrying a credential-shaped literal
- **When** the guard scans the tree
- **Then** both are reported as `key-shaped-literal`
- **Test:** tests/test_secret_output.py::test_a_leaked_value_in_a_non_code_file_is_a_violation

#### Scenario: a value pasted into a document

- **Given** a `README.md` whose prose quotes the forbidden shapes AND carries a real credential-shaped value
- **When** the guard scans it
- **Then** the value is reported and the quoted shapes are not
- **Test:** tests/test_secret_output.py::test_a_document_quoting_the_forbidden_shape_is_not_a_violation

#### Scenario: a binary or empty file

- **Given** a tree with a binary blob containing a credential shape, and an empty file
- **When** the guard scans it
- **Then** neither is a finding
- **Test:** tests/test_secret_output.py::test_a_binary_or_empty_file_is_never_a_finding

### Requirement: Command-shaped rules apply only where commands run

The rules that describe EXECUTION (a printed value, a value on `argv`, an env dump, a
piped stdout, `set -x`) MUST apply only to files whose lines are commands, so a document
that explains the rule is not itself a violation; the shape rules still apply there.

#### Scenario: a proposal explaining the forbidden shape

- **Given** `openspec/changes/x/proposal.md` and `README.md` quoting `echo "$HF_TOKEN"` and `| tee /dev/stderr` as prose
- **When** the guard scans them
- **Then** no violation is reported
- **Test:** tests/test_secret_output.py::test_a_document_quoting_the_forbidden_shape_is_not_a_violation
