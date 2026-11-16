# measurement-ingest

## ADDED Requirements

### Requirement: A refusal repeated across snapshots prints once, naming its repetitions

Ingest refusal seams that reject the same `(rule, model, engine, source post)` in
several snapshots MUST print ONE `[ingest] REFUSED` line for the run, naming how
many times it was seen and which snapshots showed it; the refusal itself, its
ledger record and the run-level refusal COUNT MUST be unchanged (log noise may
shrink, evidence never may), and two distinct refusals MUST each keep their own
line so grouping never swallows a new one.

#### Scenario: a post refused by three legs prints one grouped line

- **Given** one cross-model copy tuple carried by three snapshots
  (`amd-re.json`, `cpu-re.json`, `nvidia-re.json`) re-ingested in one run
- **When** `ingest_raw_snapshots` finishes the run's grouped refusal flush
- **Then** exactly one `[ingest] REFUSED cross-model duplicate measurement` line
  names that post, carries `seen 3x across snapshots` with the three file names,
  and the copy is still refused (it never merges)
- **Test:** tests/test_ingest_refusal_grouping.py::test_a_post_refused_by_every_leg_prints_one_grouped_line

#### Scenario: distinct refusals each keep their own line

- **Given** two different refusals in one run (a cross-model copy on one post, a
  fabricated engine on another)
- **When** the grouped flush prints the run's refusals
- **Then** each gets its own line and a refusal seen once carries no repetition
  suffix
- **Test:** tests/test_ingest_refusal_grouping.py::test_distinct_refusals_each_still_get_their_own_line

#### Scenario: the shipped raw replay dedupes per post and rule without shrinking counts

- **Given** all shipped `data/raw/*.json` snapshots replayed against a copy of the
  shipped store
- **When** the run's `[ingest] REFUSED` lines are parsed per
  `(rule, engine, model, post)`
- **Then** no key prints more than once, at least three real re-captured posts
  report as grouped repetitions, and the run's refusal COUNT line states a number
  strictly greater than the grouped line count
- **Test:** tests/test_ingest_refusal_grouping.py::test_shipped_raw_replay_reports_each_refusal_once_per_post_and_rule

#### Scenario: every seam feeds the grouped flush

- **Given** `scripts/update_trending.py`'s `ingest_raw_snapshots`
- **When** the wiring is read
- **Then** the cross-model seam records through
  `_note_run_refusal(run_refusals, "cross-model duplicate measurement"` and the
  flush prints `"[ingest] REFUSED {rule} …"` once per key
- **Test:** tests/test_cross_model_attribution.py::test_cross_model_refusal_is_wired_into_ingest
