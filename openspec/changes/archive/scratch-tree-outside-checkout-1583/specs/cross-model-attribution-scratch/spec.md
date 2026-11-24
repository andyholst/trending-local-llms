## ADDED Requirements

### Requirement: The ingest-replay scratch tree in test_cross_model_attribution is built outside the checkout

`tests/test_cross_model_attribution.py` SHALL build its `tmp-ig702-e2e` replay tree under a `tempfile.mkdtemp()` directory OUTSIDE the repository checkout, and SHALL NOT leave a `tmp-ig702-*` entry behind inside the checkout after a run. A surviving in-checkout tree is one `git add -A` away from being committed by any lane.

#### Scenario: The replay tree lives outside the checkout

- **Given** the module's `_scratch(prefix)` seam
- **When** the E2E replay test asks for a scratch tree
- **Then** the returned path is not equal to `ROOT` and does not have `ROOT` among its parents
- **Test:** tests/test_cross_model_attribution.py::test_scratch_tree_is_built_outside_the_checkout_and_leaves_no_residue

#### Scenario: No residue inside the checkout

- **Given** the module has run its E2E replay test
- **When** the checkout is scanned for `tmp-ig702-*`
- **Then** no such entry remains inside `ROOT`
- **Test:** tests/test_cross_model_attribution.py::test_scratch_tree_is_built_outside_the_checkout_and_leaves_no_residue

### Requirement: Scratch-tree removal in test_cross_model_attribution is loud

Removing a scratch tree in `tests/test_cross_model_attribution.py` SHALL raise on failure rather than pass `ignore_errors=True`; a silent survival is the defect this change removes.

#### Scenario: A failing removal raises

- **Given** a path that is a regular file, not a directory
- **When** `_remove(path)` is called
- **Then** it raises an `OSError` instead of returning quietly
- **Test:** tests/test_cross_model_attribution.py::test_a_failing_removal_raises_loudly

#### Scenario: A healthy removal leaves nothing

- **Given** a scratch tree built by `_scratch`
- **When** `_remove` is called on it
- **Then** the path no longer exists
- **Test:** tests/test_cross_model_attribution.py::test_a_failing_removal_raises_loudly
