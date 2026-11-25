# Proposal: owed-row-prose-quote-discriminator

Issue: #1690

## Why

`bot_markers.parse_owed_rows` ran `OWED_ROW_RE` over the WHOLE thread text, and that regex matches
the literal substring anywhere — including inside a code span that QUOTES a marker. Measured with
the repo's own parser over the real #1685 thread (captured through `gh api`, composed exactly as
`owed_rows_check.read_thread` does): FOUR rows came back where ONE declaration exists — three
`section=8 needle=test_a_planted_json_projection_path_is_refused` (one genuine `- **Owed-row:**`
on the issue body plus two inline-code quotations in comments) and one phantom
`section=6r needle="make pipeline-failure-issue"` (a comment quoting #1581's malformed marker).
`make owed-rows-check REPO=andyholst/trending-local-llms` therefore printed
`[owed-rows] #1685 section=6r NO SUCH SECTION` and reported `problems=2`.

A phantom row is not cosmetic: `NO SUCH SECTION` can never read `LANDED`, so the whole ledger stays
red and the per-line acceptance of the issue it appears on becomes unsatisfiable.

## What Changes

- **`scripts/bot_markers.py`** — `parse_owed_rows` strips QUOTATION before the unchanged grammar
  runs (`declaration_text`): fenced code blocks (``` ``` ```/~~~), inline code spans (`` `…` `` on one
  line) and block-quoted lines (`> …`) are removed; everything else is untouched.
- **`tests/test_bot_markers.py`** — the module that owns the parser gains four guards: the
  recorded #1685 thread yields NO phantom `section=6r` row and exactly one genuine `section=8`
  row; a findings-style body still registers its row; #1581's own `section=6r` item is still
  REPORTED (its repair stays #1581's) while the two markers inside its fenced PROPOSAL drop.
  Both threads ship as fixtures (`tests/fixtures/thread_1685_quoted_markers.txt`,
  `thread_1581_quoted_markers.txt`) so the suite needs no network.
- **`ARCHITECTURE.md`** §3 target row for `owed-rows-check` and §6 script row for
  `scripts/bot_markers.py` state the quotation rule.
- **`findings/1690.md`** declares the §8 guard row this change owes (rule 3c).

## Impact

Additive only. The marker grammar (`owed_row_marker`/`OWED_ROW_RE`), the writer, the filers, the
ledger's landing decision (`row_states`) and every other reader are unchanged. A genuine
declaration — `- **Owed-row:** <marker>` on an issue body or in a `findings/*.md` file, which is
exactly what `scripts/file_findings.py` stamps — is unquoted and still registers; only the
quotation is dropped. No data, contract, workflow or Makefile change.

## Not covered

- Only-filings-read declarations. Rejected: the ledger reads THREADS, so a hand-written
  declaration on an issue body must keep working — restricting to `findings/<issue>.md` would
  silently stop reading the declarations `file_findings` files onto issues.
- #1581's malformed `section=6r` marker itself. It stays REPORTED; repairing that body is #1581's
  act, and this change deliberately neither deletes nor launders it.
- A marker written into PLAIN prose with no quotation device at all is still a declaration under
  the existing contract; narrowing that would be a second, breaking rule change.
