## ADDED Requirements

### Requirement: A concluded-bad pipeline run is filed, not only diagnosed

`AGENTS.md` §6w's `R:` duty SHALL require that a concluded-bad run of a MAIN pipeline or of a
PR pipeline is filed through `make pipeline-failure-issue` (the ONE filer seam) and handed to
`tll-implementer`, in addition to being diagnosed and posted on the thread.

#### Scenario: A red main pipeline is filed

- **Given** an `R:` marker whose conclusion is `failure` on a main pipeline
- **When** the woken lane handles it
- **Then** it files the failure through `make pipeline-failure-issue` and hands the issue to `tll-implementer`
- **Test:** tests/test_watch_monitor.py::test_the_rulebook_requires_filing_a_red_pipeline

#### Scenario: The duty cannot be dropped silently

- **Given** the §6w text
- **When** the guard runs
- **Then** it fails if the filing duty or the filer seam's name is absent
- **Test:** tests/test_watch_monitor.py::test_the_rulebook_requires_filing_a_red_pipeline
