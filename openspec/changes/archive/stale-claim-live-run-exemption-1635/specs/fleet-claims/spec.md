## ADDED Requirements

### Requirement: A still-LIVE run is exempt from the stale-claim sweep

The sweep SHALL resolve the CI evidence attached to a run-bearing working claim through the thin
`gh` layer and SHALL emit NOTHING for a claim whose evidence is still live, at ANY age. A run id
is live while `gh run view <id> --json status,conclusion` answers `queued` or `in_progress`. An
OPEN PR is live while its NEWEST run (read with `gh run list --branch`) is not concluded. A
CONCLUDED run, a MERGED/CLOSED PR, an OPEN PR with no run, and a claim carrying neither kind of
evidence SHALL NOT be exempt; a run-bearing one SHALL keep the doubled 180/360 grace.

#### Scenario: an in_progress or queued run emits nothing past both bounds

- **Given** a signed working claim carrying `R:<id>` for a run whose `gh run view` status is
  `in_progress` or `queued`, aged 200 minutes (past the doubled STALE bound) and 400 minutes
  (past the doubled RELEASE bound)
- **When** `fetch_open_threads` + `sweep_threads` run with `liveness_resolver`
- **Then** no `S:` marker is emitted at either age
- **Test:** tests/test_stale_claim_sweep.py::test_a_still_live_run_is_exempt_and_a_concluded_one_keeps_the_doubled_pair

#### Scenario: a concluded run keeps the doubled grace

- **Given** a claim carrying `R:<id>` for a `completed` run at the same two ages
- **When** the same real path runs
- **Then** exactly one marker is emitted — `stale` at 200 minutes and `released` at 400 minutes
- **Test:** tests/test_stale_claim_sweep.py::test_a_still_live_run_is_exempt_and_a_concluded_one_keeps_the_doubled_pair

#### Scenario: an OPEN PR whose newest run is not concluded is exempt; a merged one is not

- **Given** an OPEN PR with a newest run `in_progress`, an OPEN PR with a newest run `completed`,
  a MERGED PR, and an OPEN PR with no run at all, all at the same age
- **When** `sweep_threads` resolves each PR through the stubbed `gh`
- **Then** only the OPEN PR with the unconcluded newest run emits nothing; the other three keep
  the doubled pair
- **Test:** tests/test_stale_claim_sweep.py::test_a_still_live_run_is_exempt_and_a_concluded_one_keeps_the_doubled_pair

### Requirement: The pure decision consumes a RESOLVED liveness boolean

`sweep_thread` SHALL take `live_evidence=` and, when it is True for a run-bearing claim, return an
empty verdict list before measuring age. `live_evidence=False` and `live_evidence=None` SHALL keep
the doubled pair, so a caller that cannot resolve `gh` never silently exempts a claim. A SILENT
claim (no run id or PR number) SHALL never be exempted by `live_evidence=True`. The thin layer SHALL
resolve every run id and PR number the claim text carries, not just the first.

#### Scenario: live_evidence=True exempts at any age while False/None do not

- **Given** one run-bearing claim at ages 181, 200, 360, 600 and 1440 minutes
- **When** `sweep_thread` is called with `live_evidence=True`, then with False and None
- **Then** the True calls all return `[]`; the False and None calls return the doubled `released`
  verdict; a SILENT claim with `live_evidence=True` still returns its normal verdict
- **Test:** tests/test_stale_claim_sweep.py::test_the_pure_decision_exempts_live_evidence_at_any_age

#### Scenario: every run id and PR number is extracted from the claim text

- **Given** a claim carrying `R:45123456789` and one carrying `PR #1611`
- **When** the pure extractors read those bodies
- **Then** they yield `(45123456789,)` and `(1611,)` respectively, and `{queued, in_progress}` is
  the pinned live-status set
- **Test:** tests/test_stale_claim_sweep.py::test_the_pure_decision_exempts_live_evidence_at_any_age

### Requirement: The exemption guard is RED on the shipped seam

The both-directions guard SHALL fail against `scripts/stale_claim_sweep.py` from `origin/master`:
that seam has no liveness resolution and reports a still-live claim as `released`. The read of the
pre-change source SHALL fail loudly when `origin/master` is unreadable, never pass vacuously.

#### Scenario: the same fixture is reported by the base seam and exempted by the fixed one

- **Given** the stub `gh` answering `in_progress` for `R:111` and a 400-minute-old claim
- **When** the guard feeds that fixture through BOTH the fixed module and the pre-change module
- **Then** the fixed module emits no marker, the pre-change module emits one `...:released`
  marker, and the pre-change source is asserted non-empty and free of the liveness seam
- **Test:** tests/test_stale_claim_sweep.py::test_the_live_exemption_guard_is_red_on_the_base_revision

### Requirement: The existing contract stays intact

The three authority limits, the two pinned grace pairs, every `--check` floor, the `Makefile ?=`
overrides and the `S:` marker vocabulary SHALL be unchanged by this change.

#### Scenario: the limits and floors still hold

- **Given** the shipped module and the same-age fixtures from #1626
- **When** the existing guards run
- **Then** `AUTHORITY_LIMITS == ("human", "live-run", "terminal")`, the SILENT pair is 90/180 min,
  the run-bearing pair is 180/360 min, a bound below its floor is refused with exit 2, and a
  HUMAN/TERMINAL claim at 120 min still emits nothing while a SILENT one emits `stale`
- **Test:** tests/test_stale_claim_sweep.py::test_the_three_authority_limits_emit_nothing_at_the_same_age

#### Scenario: a run-bearing claim still gets the doubled bound without resolution

- **Given** a run-bearing claim at 120 and 200 minutes resolved to `None`
- **When** the pure decision runs without a resolver
- **Then** it behaves exactly as before #1635: fresh below 180 min, `stale` at or above 180 min
- **Test:** tests/test_stale_claim_sweep.py::test_a_run_bearing_claim_gets_the_doubled_bound
