# secret-scan

## ADDED Requirements

### Requirement: The gate's file set is what git could commit

`make secret-scan` SHALL scan the full checked-out tree (staged and unstaged
new files included) and decide its verdict over the file set **git could
commit**: a finding on a path git itself refuses to stage — decided by git's
own `git check-ignore`, never a hand-maintained path list — is reported as a
gitignored build artifact and MUST NOT fail the gate; a finding in any other
file MUST fail it. The decision has exactly ONE implementation, reached
through the Makefile (rules 6d/6m).

WHEN a scan reports findings,
THEN each finding is classified by `git check-ignore`, findings in committable
files fail with exit 1, findings only on gitignored paths exit 0 while naming
every one of them, and a scan that produced no parseable report exits 2 loudly.

#### Scenario: findings only in gitignored build artifacts never block the gate

- **Given** a scan report whose every finding lives under a path the repository
  gitignores (e.g. `tests/__pycache__/*.pyc` after `make test`)
- **When** `scripts/secret_scan_report.py` renders the verdict
- **Then** it exits 0 and names each finding as a gitignored artifact
- **Test:** `tests/test_secret_scan.py::test_scan_report_filter_decides_the_fileset`

#### Scenario: a finding in a committable file still fails the gate

- **Given** a scan report with one finding in a gitignored cache and one in a
  committable file
- **When** the verdict is rendered
- **Then** it exits 1 naming the committable file, and still lists the ignored
  artifact rather than hiding it
- **Test:** `tests/test_secret_scan.py::test_scan_report_filter_decides_the_fileset`

#### Scenario: a scan that wrote no report is never a silent clean

- **Given** a verdict request for a scan report that does not exist or cannot be
  parsed
- **When** `scripts/secret_scan_report.py` is asked for a verdict
- **Then** it exits 2 and says the scan input is broken, never reporting clean
- **Test:** `tests/test_secret_scan.py::test_scan_report_filter_decides_the_fileset`

#### Scenario: the exemption can never swallow a real finding

- **Given** a throwaway git repository holding the planted fake BOTH in a
  tracked file and in its gitignored `__pycache__/`
- **When** `make secret-scan-self-test` runs the real scan and the real verdict
- **Then** the gate goes red on the tracked fake, and with the tracked fake
  removed the same artifact-only tree goes green
- **Test:** `scripts/secret_scan_self_test.py` (the #836 direction; run by
  `make secret-scan-self-test` in qa-validate's `validate` job)

#### Scenario: the Makefile keeps the verdict in the filter, not in gitleaks' exit code

- **Given** the `_secret-scan` recipe
- **When** its shape is pinned
- **Then** it writes a JSON report, passes `--exit-code 0` to gitleaks, runs
  `python3 scripts/secret_scan_report.py` as the verdict, and deletes the
  report inside the same recipe
- **Test:** `tests/test_secret_scan.py::test_targets_exist_and_are_pinned`
