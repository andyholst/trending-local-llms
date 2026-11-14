# Tasks — owed-row-close-quote (#766)

- [x] `row_states` extracted as the pure landing decision; the report walks it, report output byte-identical (`tests/test_owed_rows.py` green)
- [x] `owed_row_close_note` added: LANDED with `AGENTS.md:<line>` proof / OUTSTANDING; raises on unreadable thread/rulebook, malformed marker, missing section
- [x] `issue_verdict.py` quotes the note in the `close` comment; a ledger-read failure refuses the close (exit 2, nothing written); `--agents-file` names the rulebook; plain closes unchanged
- [x] `tests/test_issue_triage.py` locks the five close-path outcomes end to end (stub `gh`, product code runs for real) — 131/131 green
- [x] `tests/test_owed_rows.py` locks report↔note parity and the raise-on-broken-read — 12/12 green
- [x] `make lint` green on the change (linefeeds, agent-skill, guard wiring)
- [x] AGENTS.md §8 carries the new guard row (rule 6c) and §6e names the close quote (rule-3c: declared in a comment on #766)
- [x] `make test` green end to end
- [x] OpenSpec change archived with its `PR:` recorded by `make openspec-record-pr` and the index regenerated
