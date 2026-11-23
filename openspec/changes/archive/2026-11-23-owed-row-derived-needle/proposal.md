# Proposal: owed-row-derived-needle

Issue: #1367

## Why

`make owed-rows-check REPO=andyholst/trending-local-llms` reported `[owed-rows] #1357 section=8 needle='tests/test_watch_monitor.py' LANDED AGENTS.md:2439`, but `grep -c run_prs AGENTS.md` answers `0` — the §8 row was never extended. The marker was DERIVED by `scripts/owed_row_derive.py`, whose `_NEEDLE_PATTERNS` is first-match-wins and picked the module name out of the Done-when text, a name §8 already carries, so the declaration read as satisfied before anyone landed it.

A `LANDED` no edit earned is exactly the rule-3c starvation the ledger exists to prevent: the issue reads as landed, the rulebook keeps describing the pre-#1355 behaviour, and a later edit can drop the `run_prs` map with nothing naming the loss.

## What Changes

- `scripts/owed_row_derive.py`: a DERIVED needle that ALREADY appears inside the declared section's line span is REFUSED (`derive_rows` answers `[]`), so an EXTENSION Done-when must be stated explicitly with the new symbol through the filer's `- **Owed-row:**` field. The explicit-field path, the `NO SUCH SECTION` refusal and the "no section / no identifier named" refusals are unchanged.
- `tests/test_filer_owed_rows.py`: a guard that reds on #1357's own shape (module already in §8, `run_prs` nowhere) against BOTH a planted fixture and the REAL `AGENTS.md`, with a positive control proving the same sentence still derives when the section does not already name the module.

## Impact

The filers (`make file-findings`, `make data-gap-issue`) stamp FEWER derived markers — only ones naming something the section does not already carry. An issue whose Done-when names only an already-present module now files as `NO MARKER` unless the filer states the row explicitly, which is the honest answer. No data, contract, workflow, target or Makefile change, and no change to `owed_rows_check`'s reader or to the `bot_markers` grammar.

## Not covered

- No AGENTS.md edit: #1357's own owed row stays its own issue for an attended run (rule 3c), and this change's §8 row extension is declared as an owed row for the same reason.
