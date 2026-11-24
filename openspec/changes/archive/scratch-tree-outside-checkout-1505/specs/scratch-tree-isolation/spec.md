## ADDED Requirements

### Requirement: An ingest-replay scratch tree is built outside the checkout

`tests/test_ingest_refusal_grouping.py` SHALL build every `tmp-882-*` replay tree under a `tempfile.mkdtemp()` directory OUTSIDE the repository checkout, and SHALL NOT leave a `tmp-882-*` entry behind inside the checkout after a run. A surviving in-checkout tree is one `git add -A` away from being committed by any lane.

#### Scenario: The replay tree lives outside the checkout

- **Given** the module's `_scratch(prefix)` seam
- **When** a replay test asks for a scratch tree
- **Then** the returned path is not equal to `ROOT` and does not have `ROOT` among its parents
- **Test:** tests/test_ingest_refusal_grouping.py::test_scratch_tree_is_built_outside_the_checkout_and_leaves_no_residue

#### Scenario: No residue inside the checkout

- **Given** the module has run its replay tests
- **When** the checkout is scanned for `tmp-882-*`
- **Then** no such entry remains inside `ROOT`
- **Test:** tests/test_ingest_refusal_grouping.py::test_scratch_tree_is_built_outside_the_checkout_and_leaves_no_residue

### Requirement: Scratch-tree removal is loud

Removing a scratch tree SHALL raise on failure rather than pass `ignore_errors=True`; a silent survival is the defect this change removes.

#### Scenario: A failing removal raises

- **Given** a path that is a regular file, not a directory
- **When** `_remove(path)` is called
- **Then** it raises an `OSError` instead of returning quietly
- **Test:** tests/test_ingest_refusal_grouping.py::test_a_failing_removal_raises_loudly

#### Scenario: A healthy removal leaves nothing

- **Given** a scratch tree built by `_scratch`
- **When** `_remove` is called on it
- **Then** the path no longer exists
- **Test:** tests/test_ingest_refusal_grouping.py::test_a_failing_removal_raises_loudly
