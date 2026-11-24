## ADDED Requirements

### Requirement: A silent working-claim is swept at the grace bounds

For every OPEN issue whose NEWEST comment is a signed `BOT <lane> · working on #<id> · …` claim,
the sweep SHALL measure `age = now - createdAt` and emit ONE `S:<issue>:<claim-id>:<verdict>`
line when the age reaches the stale bound (90 min) or the release bound (180 min), with the
higher verdict winning and the lines ordered newest-last.

#### Scenario: A fresh silent claim crosses nothing

- **Given** an open thread whose newest comment is a fleet lane's working-claim 60 minutes old
- **When** the pure decision runs
- **Then** no line is emitted
- **Test:** tests/test_stale_claim_sweep.py::test_a_silent_claim_under_the_threshold_is_not_reported

#### Scenario: The stale and release bounds

- **Given** silent claims aged 120 minutes and 181 minutes
- **When** the pure decision runs
- **Then** the first emits `stale`, the second emits `released`
- **Test:** tests/test_stale_claim_sweep.py::test_a_silent_claim_over_the_threshold_reports_stale_then_released

#### Scenario: One line per claim, newest last

- **Given** two open threads with crossing claims of different ages
- **When** the sweep renders its output
- **Then** the older claim's line is printed first and each line carries the `S:` prefix
- **Test:** tests/test_stale_claim_sweep.py::test_output_is_newest_last_and_one_line_per_claim

### Requirement: A run-bearing claim gets doubled bounds

A claim whose OWN text attaches a CI run id (`R:<id>`) or a PR number (`PR #<n>`) SHALL have
BOTH bounds doubled, because CI itself consumes wall clock.

#### Scenario: CI evidence changes the verdict

- **Given** a claim aged 120 minutes carrying `R:<id>`, and another aged 200 minutes carrying it
- **When** the pure decision runs
- **Then** the 120-minute claim is still fresh while the 200-minute claim is stale, and a bare
  claim at 120 minutes IS stale
- **Test:** tests/test_stale_claim_sweep.py::test_a_run_bearing_claim_gets_the_doubled_bound

### Requirement: Human, terminal and misnumbered claims are never swept

The sweep SHALL emit nothing for a CLOSED issue, for a thread whose newest comment is not a
signed working-claim (a `done`/`handover`/`pr`/`reviewing`/`status` line), for a claim whose lane
is not one of the eight fleet lanes, or for a claim naming a different issue than its thread.

#### Scenario: A human's claim

- **Given** a host-signed note and a `BOT` line from a lane outside the fleet, both old enough to
  cross
- **When** the pure decision runs
- **Then** neither produces a line
- **Test:** tests/test_stale_claim_sweep.py::test_a_human_claim_is_never_swept

#### Scenario: An already-terminal thread

- **Given** a closed issue and open threads whose newest comment is a `done`, `pr` or `status`
  line
- **When** the pure decision runs
- **Then** none produces a line
- **Test:** tests/test_stale_claim_sweep.py::test_a_terminal_thread_is_never_swept

### Requirement: A repeated tick does not re-report a claim

`<claim-id>` SHALL be `sha1(author + created_at + issue + body)[:12]`, stable across ticks with no
state file, and the caller's `announced` set SHALL suppress an already-reported claim.

#### Scenario: Second-tick dedup

- **Given** a claim reported by the first tick and its id supplied as announced
- **When** the pure decision runs again over the same thread
- **Then** no line is emitted, and the id is unchanged from the first tick
- **Test:** tests/test_stale_claim_sweep.py::test_a_second_tick_does_not_re_report_the_same_claim

### Requirement: An unreadable thread is a loud failure

An unreadable `gh` read SHALL exit 2 naming the failure, never a partial report that reads as
"nothing is stale".

#### Scenario: A failing gh read

- **Given** a stub `gh` whose `issue view` exits non-zero
- **When** the live target runs through the real script
- **Then** it exits 2, prints `READ FAILED` and emits no verdict line
- **Test:** tests/test_stale_claim_sweep.py::test_an_unreadable_thread_exits_2_loudly

### Requirement: The offline contract needs no network

`make stale-claim-sweep CHECK=1` SHALL validate the grace ordering, the claim grammar and the
run-bearing discriminator with no network and no writes.

#### Scenario: The offline contract

- **Given** `--check` with the default grace pair
- **When** it runs
- **Then** it exits 0 and prints no verdict line; a disordered or zero pair is refused with exit 2
- **Test:** tests/test_stale_claim_sweep.py::test_the_offline_contract_needs_no_network

### Requirement: The seam is wired and described

The target SHALL exist, `qa-validate` SHALL run the offline contract, `ARCHITECTURE.md` SHALL
carry the target and script rows, and the validate gate SHALL be registered.

#### Scenario: Wiring guard

- **Given** the real tree
- **When** the wiring test reads the Makefile, the workflow, the description and the alarm table
- **Then** every row is present
- **Test:** tests/test_stale_claim_sweep.py::test_the_tree_wiring_is_complete
