# owed-row-ledger

## ADDED Requirements

### Requirement: The owed-row derivation is ONE module and states only what the text states

`scripts/owed_row_derive.py` MUST be the single derivation (rule 6d) both filers
import; no filer may re-spell its patterns. A section may be derived only from a
`§<id>` / `AGENTS.md section <id>` / `rule <id>` mention AND only when `<id>`
exists as a `## <id>.` heading in `AGENTS.md` according to
`owed_rows_check.sections()` — the ledger's own parser — and a needle may be
derived only from an identifier the text names (`make <target>`,
`tests/test_*.py`, `scripts/*.py`, `check_*`). A text that states nothing yields
no declaration; the filer then stamps nothing.

#### Scenario: a Done-when naming a real section and an identifier derives one declaration

- **Given** the Done-when "add the AGENTS.md §8 guard row for
  tests/test_derived_probe.py" and a rulebook containing `## 8.`
- **When** the derivation reads it
- **Then** it returns exactly one row `{section: 8, needle: tests/test_derived_probe.py}`
- **Test:** tests/test_filer_owed_rows.py::test_the_derivation_states_only_what_the_text_names

#### Scenario: a section that is not a heading is never stamped

- **Given** a Done-when naming `§99z` (no such `## 99z.` heading) beside a make target
- **When** the derivation reads it
- **Then** it returns `[]` — a filer can never stamp a marker the ledger would
  refuse as `NO SUCH SECTION` (exit 2)
- **Test:** tests/test_filer_owed_rows.py::test_the_derivation_states_only_what_the_text_names

#### Scenario: a stated section with no guard-row identifier derives nothing

- **Given** a Done-when naming `§8` while naming no make target, test file, script
  or `check_*` name
- **When** the derivation reads it
- **Then** it returns `[]` — the issue will read `NO MARKER`, never a fabricated needle
- **Test:** tests/test_filer_owed_rows.py::test_the_derivation_states_only_what_the_text_names

### Requirement: both filers stamp the derived marker on the issue they file

`scripts/file_findings.py` (when no explicit `- **Owed-row:**` field is present)
and `scripts/data_gap_analysis.py::issue_body()` MUST run the shared derivation
on the finding's Done-when / the composed body, and render every derived row
through `bot_markers.owed_row_marker` (the ONE writer, rule 6j) into the filed
body. Nothing derivable → no marker in the body.

#### Scenario: a finding with no explicit field still files a parseable marker

- **Given** a findings.md whose Done-when names `§8` and `tests/test_foo_derive.py`,
  with no `- **Owed-row:**` field
- **When** `make file-findings` files the issue (stub `gh` on PATH; the real script runs)
- **Then** the filed body carries exactly one
  `<!-- owed-row: section=8 needle=tests/test_foo_derive.py -->` and
  `bot_markers.parse_owed_rows` reads it back with zero malformed markers
- **Test:** tests/test_filer_owed_rows.py::test_file_findings_stamps_a_derived_row_on_the_filed_issue

#### Scenario: a Done-when that names nothing files an unmarked issue

- **Given** a findings.md whose Done-when names no section and no identifier
- **When** the filer files it
- **Then** the filed body carries no `owed-row:` marker at all
- **Test:** tests/test_filer_owed_rows.py::test_file_findings_stamps_nothing_when_the_done_when_names_nothing

#### Scenario: the data-gap filer stamps the body it composes

- **Given** a gap report whose contract-gap sentence names `AGENTS.md §8` beside
  `make owed-rows-check`
- **When** `issue_body()` composes the issue body
- **Then** the body gains a `## Owed rulebook rows` section whose marker parses to
  `{section: 8, needle: owed-rows-check}`, and a report whose text names nothing
  gains no marker
- **Test:** tests/test_filer_owed_rows.py::test_the_data_gap_filer_stamps_its_own_body

### Requirement: a filer-stamped marker reads in the ledger end to end

A marker stamped at filing time MUST be readable by the REAL
`scripts/owed_rows_check.py` without any translation: it parses through
`bot_markers.parse_owed_rows`, names a section the ledger knows, and reports as
`OUTSTANDING` (or `LANDED` once its row lands) with `problems=0` — never
malformed, never a phantom section.

#### Scenario: the real ledger reads a filed derived marker

- **Given** a stub `gh` serving one open `tech-debt` issue whose body carries the
  marker `section=8 needle=tests/test_foo_derive.py`
- **When** the real `owed_rows_check` runs against the real `AGENTS.md`
- **Then** it prints `section=8 needle='tests/test_foo_derive.py' OUTSTANDING`
  and `problems=0`, exiting 0
- **Test:** tests/test_filer_owed_rows.py::test_a_filed_derived_marker_reads_in_the_real_ledger
