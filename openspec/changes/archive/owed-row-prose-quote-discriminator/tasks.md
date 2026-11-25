# Tasks: owed-row-prose-quote-discriminator

- [x] RED-first guards in `tests/test_bot_markers.py` (the module that owns the parser): the recorded #1685 thread yields no phantom `section=6r` row and exactly one genuine `section=8` row; a findings-style body still registers; #1581's own `section=6r` item is still reported while its fenced proposal markers drop — observed RED on the base parser (`PASSED 84 | FAILED 3`, exit 1)
- [x] Record the #1685 and #1581 threads as fixtures (`tests/fixtures/thread_1685_quoted_markers.txt`, `thread_1581_quoted_markers.txt`) so the guards run offline
- [x] `scripts/bot_markers.py`: `declaration_text()` strips fenced code blocks, inline code spans and block-quoted lines; `parse_owed_rows` applies the unchanged grammar to that text — GREEN (`PASSED 88 | FAILED 0`)
- [x] Neighbouring modules green with the fix: `test_owed_rows` (12/0), `test_filer_owed_rows` (8/0), `test_file_findings` (91/0), `test_issue_triage` (141/0), `test_agents_rows` (124/0), `test_workflows` (1450/0), `test_pipeline_failure_issue` (337/0), `test_architecture` (111/0)
- [x] Live ledger read per-line on the SAME base `151321c`: base `landed=6 outstanding=32 problems=4` → head `landed=5 outstanding=24 problems=1`; `#1685 section=6r` gone, one `#1685 section=8`. Six threads changed match counts, every dropped marker verified quoted in context
- [x] Update `ARCHITECTURE.md` §3 `owed-rows-check` row and §6 `scripts/bot_markers.py` row
- [x] Write `findings/1690.md` declaring the owed §8 row (rule 3c) and regenerate `OPENSPEC.md`
- [~] Land the `AGENTS.md` §8 row naming `test_a_marker_quoted_in_prose_is_not_a_declaration` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] OpenSpec change bound to issue #1690 with proposal + Given/When/Then capability spec + ticked tasks, listed in `OPENSPEC.md`
- [x] Push with the owner identity and open a READY PR carrying `Closes #1690` in BOTH the title and the body
