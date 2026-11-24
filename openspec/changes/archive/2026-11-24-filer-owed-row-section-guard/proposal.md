# Proposal: filer-owed-row-section-guard

Issue: #1642

## Why

`make owed-rows-check REPO=andyholst/trending-local-llms` exits **2** on the fetched base
`4154e385`, so the owed-row ledger — the evidence the close gate reads (rule 6g / issue #766) —
is untrustworthy for EVERY reader, including `queued-alarm.yml`'s `make owed-rows-check` step:

```text
[owed-rows] #1581 section=6r NO SUCH SECTION in AGENTS.md (known: 1, 2, 3, 4, 5, 5b, 6, 6b, 7, 7b, 8)
[owed-rows] andyholst/trending-local-llms: landed=5 outstanding=17 no-marker=80 problems=1
[owed-rows] FAILED: 1 unreadable/malformed item(s) — the ledger is not trustworthy until they are fixed
```

Root cause: `scripts/file_findings.py` validated an explicit `- **Owed-row:**` field only through
`bot_markers.parse_owed_rows` (the GRAMMAR), never against `owed_rows_check.sections()` — the ONE
heading parser the ledger reads. `scripts/owed_row_derive.py` drops ids that are not headings, but
that guard runs for DERIVED rows only, so a hand-written field bypassed it. Issue #1581 therefore
carries `<!-- owed-row: section=6r needle="make pipeline-failure-issue" -->`, and `6r` is a
numbered RULE inside `## 2.`, not a `## <id>.` heading.

## What Changes

- `scripts/file_findings.py` refuses an explicit `- **Owed-row:**` whose declared section id is not
  a `## <id>.` heading in `AGENTS.md` — loudly (`[findings] FAIL …`), exit 1, BEFORE any
  `gh issue create`. The check reuses `owed_rows_check.sections()` (no second heading parser,
  rule 6d); the derived path is unchanged.
- `tests/test_filer_owed_rows.py` gains one guard: the measured `section=6r` shape is refused with
  nothing filed, and the SAME field naming a real heading (`section=8`) still files exactly one
  issue (non-vacuous).

## Impact

- `scripts/file_findings.py` — the explicit-field branch of `parse()` plus one import. No make
  target changes; `make findings-check` / `make file-findings` are the callers.
- `tests/test_filer_owed_rows.py` — one new test (RED on `origin/master`'s script:
  `PASSED 7 | FAILED 1`; green here `PASSED 8 | FAILED 0`).
- `AGENTS.md` §8 — the EXISTING row for `tests/test_filer_owed_rows.py` must be extended to name
  the new guard. Protected agent-instruction file: a headless leg records it as an OWED ROW
  (rule 3c), declared in `findings/1642.md`.
- Existing filings are unaffected: every explicit field with a valid section passes, and the
  derived path already filtered unknown sections.

## Not covered

- The data-gap filer (`scripts/data_gap_analysis.py`): it derives only and never accepts an
  explicit field, so it cannot produce the malformed shape.
- Correcting the already-filed `#1581` body: editing another bot's issue body is the reviewer's
  verb (rule 6j), not an implementation.
- The ledger's own tolerance: `owed_rows_check` keeps refusing a missing section loudly (exit 2) —
  the fix moves that refusal to FILING time, where the author can act on it.
