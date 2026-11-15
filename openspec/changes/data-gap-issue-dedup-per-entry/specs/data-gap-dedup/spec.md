# data-gap-issue-dedup

## ADDED Requirements

### Requirement: a gap issue is filed per signature entry, not per set

The post-refresh gap filer MUST dedup by signature ENTRY: each entry
(`missing:context_tokens`, `starved_leg:cpu`, …) carries its own `data-gap-signature`
marker in the issue body, and `already_filed()` is consulted per entry, so a refresh
re-files ONLY the entries with no open issue. A fluctuating `starved_leg` entry must
never re-file the persistent dimensions that already sit behind an open issue — those
stay one open issue until closed, while a starved leg still files once while starved.

#### Scenario: a fluctuating starved_leg does not re-file the persistent dimensions

- **Given** a refresh whose gap set has four persistent `missing:<dim>` entries and a
  `starved_leg:cpu` entry, which files one issue claiming all five entries (one marker
  each)
- **When** the next refresh's signature differs from the first ONLY by the volatile
  entry — `starved_leg:cpu` recovers and `starved_leg:amd` takes its place, the four
  `missing:` entries unchanged — and that volatile starved_leg has no open issue
- **Then** `already_filed()` per entry finds an OPEN issue carrying each persistent
  entry's marker (so NO second filing of the persistent dimensions), filed a single new
  issue claiming ONLY the new `starved_leg:amd` entry, and each persistent dimension
  remains claimed by exactly one issue
- **Test:** tests/test_data_gap_analysis.py::test_a_fluctuating_starved_leg_refiles_only_the_new_entry

#### Scenario: the filed issue carries one marker per claimed entry

- **Given** a report whose signature has several entries
- **When** `issue_body()` renders the gap issue for those entries (no pre-existing open
  issues)
- **Then** the body carries one `<!-- data-gap-signature: <entry_id> -->` marker for
  each entry (not one whole-set hash), the body ends with a newline, and
  `already_filed(entry_id(entry))` can later find the issue by any single entry's marker
- **Test:** tests/test_data_gap_analysis.py::test_a_gap_set_is_filed_once and the
  `_GH_STUB`/`_GH_STUB_LABELS` fixtures

#### Scenario: an unchanged gap set still files nothing

- **Given** a baseline equal to the current signature
- **When** the filer runs `--issue`
- **Then** it files nothing (the whole-set `changed()` gate still holds, unchanged from
  before)
- **Test:** tests/test_data_gap_analysis.py::test_one_issue_per_changed_gap_set

### Requirement: a recently-judged dimension MUST NOT be re-filed

The #491 guarantee is preserved at entry granularity: a CLOSED issue carrying an entry's
marker MUST record its dimension as judged, and that dimension MUST NOT be re-filed inside
`JUDGED_DAYS`. This binds per entry now (a closed starved-leg issue judges nothing about
the persistent dimensions), never per whole set.

#### Scenario: a closed entry's dimension is not re-filed inside the judged window

- **Given** a closed issue carrying an entry's marker with a `closedAt` inside
  `JUDGED_DAYS`
- **When** the same entry is seen again
- **Then** it is not re-filed, and the baseline records the judged stamp
- **Test:** tests/test_data_gap_analysis.py::test_a_closed_dimension_is_not_re_filed_inside_the_window

#### Scenario: a stale judged dimension is re-filed

- **Given** a closed issue whose `closedAt` is older than `JUDGED_DAYS`
- **When** the same entry is seen again
- **Then** it is re-filed (the judgement window has expired)
- **Test:** tests/test_data_gap_analysis.py::test_a_closed_dimension_is_not_re_filed_inside_the_window
