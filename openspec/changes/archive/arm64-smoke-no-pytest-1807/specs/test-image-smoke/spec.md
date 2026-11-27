## ADDED Requirements

### Requirement: The arm64 smoke proves the test layer using libraries the test image ships

`make test-image-smoke` SHALL run one `docker run --rm --platform linux/arm64` against
the exact published tag and SHALL import the test-layer libraries declared in
`requirements-test.txt`. It SHALL NOT import pytest, which the test image deliberately
does not carry (issue #768). The proof SHALL remain a real import under arm64, so a
broken test layer still fails the smoke.

#### Scenario: The smoke no longer imports pytest

- **Given** the `test-image-smoke` recipe on the branch head
- **When** the recipe's `python3 -c` line is read
- **Then** it imports `markdown_it` and `tabulate` and contains no `pytest` token
- **Test:** tests/test_image_manifest_check.py::test_the_arm64_smoke_proves_the_test_layer_without_pytest

#### Scenario: The base revision is refused by the same guard

- **Given** the pristine `origin/master` Makefile whose smoke imports `pytest, markdown_it, tabulate`
- **When** the new guard runs against that tree
- **Then** it reports at least one FAIL naming the recipe and exits non-zero
- **Test:** tests/test_image_manifest_check.py::test_the_arm64_smoke_proves_the_test_layer_without_pytest

### Requirement: The guard locks the dependency contract, not the image publish

The existing arm64 run-proof wiring SHALL stay intact: the workflow calls the make
target, the docker run and the `python3 -c` line live in the Makefile, the proof runs
after the manifest check, and `requirements-test.txt` SHALL NOT declare pytest.

#### Scenario: The workflow still reaches the proof through the Makefile

- **Given** `refresh-bot.yml`'s `test-image` job and the Makefile
- **When** `test_the_arm64_run_proof_steps_exist` and `test_the_target_is_makefile_only_and_wired` run
- **Then** `make test-image-smoke` is called after the manifest check and no raw `python3 -c` appears in the workflow
- **Test:** tests/test_image_manifest_check.py::test_the_arm64_run_proof_steps_exist

#### Scenario: The test image's declared dependencies have no pytest

- **Given** `requirements-test.txt` in the branch tree
- **When** the new guard reads it
- **Then** no `pytest` entry is present and the guard says so with an `ok` line
- **Test:** tests/test_image_manifest_check.py::test_the_arm64_smoke_proves_the_test_layer_without_pytest
