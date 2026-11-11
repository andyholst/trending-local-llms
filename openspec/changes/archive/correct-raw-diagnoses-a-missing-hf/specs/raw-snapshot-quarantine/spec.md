# raw-snapshot-quarantine

## ADDED Requirements

### Requirement: The quarantine report names what the row carried that could have become `hf`

When `scripts/self_correct_raw.py` quarantines a model row whose `hf` cannot be
derived, its ONE `QUARANTINED:` line MUST carry a diagnosis of the captured
evidence: the model, the reason, the row's `source_post`(s) — and whether the row
(or, failing that, the rest of its snapshot) carried any HF-shaped token, naming
the field it was found in and quoting the captured text in a BOUNDED form. The
line MUST distinguish a row that HELD a repo id and never put it in `hf` from a
row that states none at all, and it MUST never invent a repo id. The quarantined
row set, the exit code and the snapshot write rule are unchanged.

#### Scenario: the row held an HF link in free text

- **Given** a raw snapshot whose model row has no `hf` but whose `why` field contains `https://huggingface.co/Qwen/Qwen3.6-27B`
- **When** `scripts/self_correct_raw.py` runs
- **Then** the `QUARANTINED:` line names the field `why`, quotes the captured link, and says it never reached `hf`, so a reader can tell the agent omitted a repo it had
- **Test:** tests/test_raw_quarantine.py::test_a_row_that_held_a_repo_says_so_in_the_report

#### Scenario: the row states no repo at all

- **Given** a raw snapshot whose model row has no `hf`, no `formats` entry with an `hf`, and no HF-shaped token anywhere in the captured text
- **When** the correction runs
- **Then** the `QUARANTINED:` line says no HF-shaped token exists anywhere in the snapshot and that none was omitted, and it still names the model and its post

- **Test:** tests/test_raw_quarantine.py::test_a_row_that_states_no_repo_says_that_too

#### Scenario: a format carried the repo

- **Given** a model row with no top-level `hf` but `formats[0].hf` set to an `owner/repo` id
- **When** the correction runs
- **Then** the `QUARANTINED:` line names `formats[0].hf` and quotes that id, so the cause is a copy, not a gap

- **Test:** tests/test_raw_quarantine.py::test_a_format_hf_is_reported_as_the_rows_repo

#### Scenario: an `hf` was captured but is malformed

- **Given** a model row whose `hf` holds a value that cannot be reduced to `owner/repo`
- **When** the correction runs
- **Then** the `QUARANTINED:` line says that value was captured and is malformed, not absent

- **Test:** tests/test_raw_quarantine.py::test_a_malformed_hf_is_reported_as_malformed

#### Scenario: a sibling row carried the only token

- **Given** a raw snapshot whose offending row states no HF-shaped token while ANOTHER model's row in the same snapshot carries one (in its `hf` or in free text), with the offending row first in one run and last in another
- **When** the correction runs
- **Then** the offending row's `QUARANTINED:` line says THIS row states none and names the sibling field that carried one, so a leg that lost the field on every row is distinguishable from a post that states no repo — and the answer does not depend on which row was quarantined first

- **Test:** tests/test_raw_quarantine.py::test_a_sibling_rows_token_is_not_claimed_as_this_rows

#### Scenario: the report stays bounded

- **Given** a row carrying a very long HF-shaped token in its captured text
- **When** the correction runs
- **Then** the quoted token in the report is truncated to a bounded length and the line stays one line

- **Test:** tests/test_raw_quarantine.py::test_a_row_that_held_a_repo_says_so_in_the_report

### Requirement: The diagnosis never changes what is quarantined

The diagnosis is report-only: the set of excluded rows, the exit code and
whether the snapshot is rewritten MUST be exactly what they were before it
existed, so a diagnosed row is still excluded and the rest of the capture still
merges.

#### Scenario: a diagnosed row is still excluded and the rest still merges

- **Given** a snapshot holding one good model and one hf-less row that carries an HF link in `why`
- **When** the correction runs
- **Then** it exits 0, the diagnosed row is gone from the file, the good model remains and the file still conforms to `data/search_contract.json`

- **Test:** tests/test_raw_quarantine.py::test_a_row_that_held_a_repo_says_so_in_the_report
