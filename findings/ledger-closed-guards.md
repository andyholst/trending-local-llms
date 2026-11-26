# Findings — ledger attribution for closed pipeline failures

## Four closed run-failure issues and #1747 lacked fix-PR/guard attribution

- **Evidence:** `make pipeline-failure-guard-check` RED on master `37c6d88`: issues #1732/#1734 (cancelled image-prep runs), #1733 (pin 0.23.3 vs 0.23.4), #1735 (arm64 exec-format) were CLOSED while their ledger rows still had `fix_pr: null`/`guard: null`; issue #1747 was CLOSED with no ledger row at all for run `45657191852`.
- **Why:** rule 3b makes the ledger append-only, so closing an issue without recording the change and the test that keep it fixed makes every later PR red and hides which delivery actually resolved the failure.
- **Done when:** the four rows name their landed fix PRs (#1741, #1725, #1742) and collected guard test files, a new row records run `45657191852` → #1747 with fix PR #1762 and `tests/test_workflows.py`, and `make pipeline-failure-guard-check` exits 0 (measured: 24 diagnosed failures attributed, 0 unguarded).
