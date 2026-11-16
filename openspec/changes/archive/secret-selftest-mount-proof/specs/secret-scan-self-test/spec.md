# Secret self-test mount proof

## ADDED Requirements

### Requirement: the self-test probe's mounts and no-report refusal are pinned by a hermetic test

`tests/test_secret_scan_selftest_mounts.py` MUST run the real `scripts/secret_scan_self_test.py`
with only the external docker CLI replaced by a PATH stub, and assert: (a) every scan/out mount
the probe builds lives under the repo-local `.secret-self-test-tmp/` scratch dir — never under
the host temp dir, which the test parks OUTSIDE the repo; (b) when the scan writes no report the
probe exits non-zero naming the missing report, never a clean tree; (c) with a scanner-shaped
stub that behaves, the probe's plant/clean/gitignored-cache directions all land.

#### Scenario: an empty mounted tree is a loud failure, never a clean tree

- **Given** the probe running against a scanner stub that "succeeds" but writes NO report
  (the measured macOS-colima false green of issue #840)
- **When** `tests/test_secret_scan_selftest_mounts.py` runs
- **Then** the probe exits 1 and its output names "wrote no report" and the mount-failure
  hypothesis
- **Test:** tests/test_secret_scan_selftest_mounts.py::test_an_empty_mounted_tree_fails_loudly_never_clean

#### Scenario: every probe mount stays repo-local even when TMPDIR points elsewhere

- **Given** TMPDIR parked in a foreign scratch dir outside the repository
- **When** the probe builds its docker mounts
- **Then** every scan/out mount source resolves under `ROOT/.secret-self-test-tmp/` and none
  is under the parked temp dir (the same test run against the pre-#836 TMPDIR-scratch probe
  fails here — mutation-verified)
- **Test:** tests/test_secret_scan_selftest_mounts.py::test_every_probe_mount_is_repo_local_never_the_host_tmpdir

#### Scenario: the probe's own directions are not green by accident

- **Given** a scanner stub that behaves like gitleaks (flags the planted credential shapes,
  stays quiet on the clean fixture)
- **When** the probe runs end-to-end against it
- **Then** detect/clean/gitignored-artifact all land with exit 0
- **Test:** tests/test_secret_scan_selftest_mounts.py::test_with_a_stub_scanner_all_probe_directions_land
