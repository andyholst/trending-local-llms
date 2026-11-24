## ADDED Requirements

### Requirement: The detector registry accepts the S marker

`scripts/watch_monitor.py` SHALL include `S:` in `MARKER_PREFIXES`, and the offline contract
SHALL accept it as a legal marker prefix.

#### Scenario: The offline contract accepts S and still refuses an unknown prefix

- **Given** `make watch-monitor CHECK=1` with no network and no state file
- **When** the contract runs
- **Then** `S:` is reported as a legal prefix, `--check` exits 0, and an unknown prefix is still refused
- **Test:** tests/test_watch_monitor.py::test_offline_check_mode

### Requirement: The seam documents the S marker

The module docstring SHALL enumerate `S:<issue>:<claim-id>:stale|released` beside the other
detector markers, so a reader learns the shape from the ONE seam.

#### Scenario: The docstring carries the S marker

- **Given** the module source at `scripts/watch_monitor.py`
- **When** a reader inspects the marker list
- **Then** the `S:` shape is documented
- **Test:** tests/test_watch_monitor.py::test_offline_check_mode
