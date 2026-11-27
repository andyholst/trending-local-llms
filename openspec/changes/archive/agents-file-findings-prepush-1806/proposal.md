# Proposal: agents-file-findings-prepush-1806

Issue: #1806
PR: #1853

## Why

The fast offline pre-push guard added in #1804/PR #1805 refuses a host push of
an implementation PR whose per-issue analysis file is missing, but `AGENTS.md`
§8 never named it. `findings/1804.md` declared the owed row with a
`section=8 needle=test_prepush_guard_refuses_a_missing_analysis` marker, and
`make owed-rows-check` reads the §8 table rather than the findings files, so the
guard's rulebook home stayed OUTSTANDING. Rule 6h requires a guard row to name
the behaviour it locks; the owner granted explicit rule-3c sign-off (comment
`7230162560`) for the exact one-line replacement in design `7219073743`.

## What Changes

- Replace the EXISTING `tests/test_file_findings.py` (rule 6g, issue #172) row
  at `AGENTS.md:2381` with the owner-signed text, extending it to name the three
  `test_prepush_guard_*` functions and the fast offline pre-push guard on
  `findings-check-for-pr PREPUSH=1 ISSUE=<n>`.
- One line changed (`@@ -2381 +2381 @@`): no added or removed row, no header
  change, no change to the other `tests/test_file_findings.py` row at line
  2484, no `#1666` / mixed-shape wording.

## Impact

- `AGENTS.md` §8 — one row extended in place; the owed-row ledger then reports
  the needle as LANDED with `AGENTS.md:2381` evidence.
- `findings/1806.md` — this analysis record.
- No workflow, data, README, skill, or schedule change; no breaking change and
  no new capability beyond naming an already-shipped guard.

## Not covered

- The mixed-shape guard row open #1666 targets; that landing is independent and
  must be signed separately.
- Any other §8 row, especially the `#659` owed-row row at line 2484.
