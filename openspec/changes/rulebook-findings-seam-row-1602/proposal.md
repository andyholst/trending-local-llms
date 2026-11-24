# Proposal: rulebook-findings-seam-row-1602

Issue: #1602

## Why

`tests/test_findings_seam.py` shipped in #1493 (landed by PR #1592) — the per-issue
analysis-file seam and its guard suite — but `AGENTS.md` §8, the table that states what
each guard catches, carries no row naming it. An unlisted guard is invisible to the next
reader deciding whether a behaviour is locked, so the sibling-collision guarantee looks
unguarded and can be quietly weakened.

Measured at base `c7fa437e` (`origin/master` fetched on asimov@mac): the needle
`tests/test_findings_seam.py` appears **0** times in `AGENTS.md`, and the owed-row ledger
reports `#1602 section=8 needle='tests/test_findings_seam.py' OUTSTANDING`. The guard
itself is landed and green on that base: `python3 tests/test_findings_seam.py` →
`PASSED 21 | FAILED 0`.

This is the rule-3c-declared §8 row. Rule 3c makes `AGENTS.md` protected: design →
reviewer sign-off → implement. The reviewer signed ACCEPT on #1602
(`issuecomment-7133012801`), reproducing the exact row and pin byte-for-byte; this landing
applies that text VERBATIM.

## What Changes

- `AGENTS.md` §8 gains ONE row for `tests/test_findings_seam.py`, inserted immediately
  after the `tests/test_push_and_verify_guard.py` row, keeping the table's two-cell shape.
  It names all five guard functions, the rules they serve, the defect they prevent and the
  fact that the module pins the row names-only.
- `tests/test_findings_seam.py` gains ONE function,
  `test_rulebook_section_8_carries_the_analysis_seam_row`, plus its single call in
  `main()`. No new file and NO Makefile/target change — `scripts/run_tests.sh` globs
  `test_*.py`, so the suite is discovered already.

§8 ONLY. No §7b bullet and no clause appended to the shared `Rule 3c note`: the guard suite
and its behaviour already shipped in #1493, only the table row stating what it catches was
owed — the same §8-only shape as #1005/#998/#1062.

## Impact

Rulebook prose plus one deterministic pin test in an existing module. No data, contract,
schema, API, table, workflow or cron change; the diff is additive (+1 `AGENTS.md` line,
+1 test function). The `AGENTS.md` edit is review-required under rule 3c, signed off by
`tll-reviewer` on #1602 before any implementer touched it.

RED on the base (pin added without the row): `exit 1`, 5 FAIL lines. GREEN on the landing
head: `PASSED 26 | FAILED 0`. The real ledger moves `OUTSTANDING` →
`LANDED AGENTS.md:2503`.

## Not covered

- §7b: deliberately untouched (rule-3c ruling on #1602).
- The three sibling rule-3c rows (#1482/#1589/#1586): disjoint regions, separate landings.
- A stricter pin over the row's three unpinned function names (recorded residual on #1602;
  planner may file a follow-up).
