# Tasks: secret-selftest-mount-proof

- [x] New hermetic test runs the REAL probe with a PATH docker stub — verified:
      `python3 tests/test_secret_scan_selftest_mounts.py` PASSED 9 | FAILED 0, and the
      sibling `tests/test_secret_scan.py` stays PASSED 52 | FAILED 0
- [x] Prove the guard bites on the old shape: mutating the probe back to default-TMPDIR
      scratch (pre-#836) turns the mount checks RED (2 FAILED), and the script is restored
      byte-clean (`git diff` empty)
- [x] Spec scenarios each carry a `Test:` line naming a real test — verified:
      `make openspec-check` green on this branch
