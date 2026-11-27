# Tasks: arm64-smoke-no-pytest-1807

- [x] `test-image-smoke` imports only the libraries the test image ships (`markdown_it`, `tabulate`), no pytest
- [x] `tests/test_image_manifest_check.py` no longer pins `"import pytest"` in the Makefile
- [x] New guard asserts the smoke imports the shipped libraries, never pytest, and that `requirements-test.txt` has no pytest — ran `python3 tests/test_image_manifest_check.py`: 37 passed, 0 failed
- [x] Guard proven RED on the pristine base tree (`git archive origin/master` + the new module): 35 passed, 2 failed, both naming the offending recipe
- [x] `findings/1807.md` written with the owed §8 row declaration
- [~] AGENTS.md §8 row naming `tests/test_image_manifest_check.py::test_the_arm64_smoke_proves_the_test_layer_without_pytest` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [~] Full `make test`, `make validate` and `make live-smoke` — blocked: CI-only on qa-validate (rule 7b; host runs fast offline checks only)
