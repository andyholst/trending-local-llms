## ADDED Requirements

### Requirement: The live redactor refuses a zero-line stream

The `scripts/scrub_log.py --stream` branch SHALL treat a producer that emits zero lines and exits 0 as the `quiet`/`agent-failed` shape — a loud, classified failure, never a clean leg, a SKIP, a retry or a source outage. On that shape it SHALL print EXACTLY ONE stderr line — `[scrub-log] FAIL: the agent stream produced 0 line(s) and exited 0 — classified quiet/agent-failed, not a source outage (issue #1820, #1747)` — and return exit code 3, before the routine `stream: N line(s)` summary. The `scrubbed_run` seam SHALL promote the redactor's non-zero status only when the producer's own status is 0, by capturing both `PIPESTATUS` values in ONE assignment and applying `if [ "$st" = 0 ] && [ "$rt" != 0 ]; then st="$rt"; fi`. Every other byte SHALL remain unchanged: the pipe segment, `PIPESTATUS[0]`, `exit "$st"`, the #1747 SIGPIPE(141) classification line, the shipped `PYTHON_RUN` runner, the `[agent]` print, `--append/--raw/--out`, and the N>0 path. No new `printf`, rule amendment or classifier branch SHALL be added.

#### Scenario: A 0-line successful producer is one classified failure

- **Given** the shipped `scrubbed_run` seam, the real redactor and a producer that sleeps, prints nothing and exits 0
- **When** the leg runs through the stand-in external CLI
- **Then** exactly one `[scrub-log] FAIL: … quiet/agent-failed, not a source outage (issue #1820, #1747)` line is printed to stderr, no `[agent]` line appears, no green `stream: 0 line(s)` summary survives, and the leg exits 3 (make reports `Error 3`)
- **Test:** `tests/test_scrubbed_run_seam.py::test_a_silent_producer_is_a_loud_classified_failure`

#### Scenario: The pre-change seam accepted the silent success (RED half)

- **Given** the same fixture against the unmodified base `b8b9ee1e8f614acbadccb006150d08f3dfa60bf3`
- **When** the new guard runs
- **Then** it FAILS with `make rc=0` and a green `stream: 0 line(s)` line, proving the defect this change removes
- **Test:** `tests/test_scrubbed_run_seam.py::test_a_silent_producer_is_a_loud_classified_failure`

#### Scenario: A talking producer still redacts every line and stays green

- **Given** an agent that emits three real lines, one carrying a credential value
- **When** the fixed seam streams it
- **Then** all three lines are printed as masked `[agent]` lines, the REDACTED artifact is non-empty, the value is never on the console, and the leg exits 0
- **Test:** `tests/test_scrubbed_run_seam.py::test_a_talking_producer_still_redacts_every_line`

#### Scenario: A failing producer keeps its own status and the 141 line is untouched

- **Given** a producer that exits non-zero and the shipped seam
- **When** the pipeline finishes
- **Then** the producer's status still wins, the #1747 SIGPIPE(141) classification line is unchanged, and `PIPESTATUS[0]` is still the producer's status
- **Test:** `tests/test_scrubbed_run_seam.py::test_a_red_command_keeps_its_exit_status_through_eval`

#### Scenario: The shipped seam contract survives the status-tail promotion

- **Given** the shipped Makefile seam with the #1808 stdin fix already on master
- **When** this change's status-tail promotion is compared against it
- **Then** `$(PYTHON_RUN)`, `PIPESTATUS[0]`, `exit "$$st"` and the #1747 SIGPIPE(141) line remain byte-identical and this change adds no runner or flag of its own
- **Test:** `tests/test_scrubbed_run_seam.py::test_the_existing_seam_contract_survives_the_promotion`

#### Scenario: Quiet and outage verdicts keep their opposite responses

- **Given** the real `zero_hit_verdict` classifier and silent-but-answered versus all-outage stats
- **When** the two stats are classified
- **Then** the unchanged classifier returns `quiet`/1 for the reachable mirror and `outage`/0 for the total outage, with no retry or SKIP added
- **Test:** `tests/test_firecrawl_fetch.py::test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search`
