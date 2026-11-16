# Secret self-test mount proof (issue #840)

## Why

`make secret-scan-self-test` once reported fine while its probe scanned **0 bytes**: macOS's
`/var/folders` TMPDIR mounted into a colima container as an empty tree, gitleaks wrote no
report, and nothing read the mount or the missing report. The probe half (repo-local scratch +
loud no-report refusal) landed in the #836/#838 change; this issue's remaining deliverable —
"host-side live check proves the throwaway tree is repo-local and an EMPTY mounted tree fails
loudly" — had no guard, so the class could silently return on any future refactor.

## What Changes

New test `tests/test_secret_scan_selftest_mounts.py` runs the REAL
`scripts/secret_scan_self_test.py` end-to-end with a PATH stub standing in for the external
docker CLI (rule 6m: external system only; the production probe code builds every mount and
decision that is asserted):

- every scan/out mount it builds lives under the repo-local `.secret-self-test-tmp/` scratch,
  never under the host TMPDIR (TMPDIR is deliberately parked outside the repo);
- a scan that writes no report exits 1 naming "wrote no report" — never a clean tree;
- with a behaving stub scanner all probe directions land (plant→detect, clean→quiet,
  gitignored bytecode→artifact-only), so the green is not a stub artifact.

## Impact

- `tests/test_secret_scan_selftest_mounts.py` (new; auto-collected by `make test`)
- Capability spec: `secret-scan-self-test`

## Not covered

- The probe script itself — unchanged (its half was fixed by #836; this is the pinned proof).
- Running the probe on a host "as a rhythm" (explicitly out of the issue's Done-when).

**Issue:** #840
PR: #1079
