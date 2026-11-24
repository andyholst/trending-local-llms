# Findings

## The AGENTS.md rows for the shape-aware analysis gate are owed to a protected rulebook

- **Signature:** owed-row-findings-shape-gate
- **Evidence:** this change adds a step to `.github/workflows/qa-validate.yml`'s `validate` job and the target `make findings-check-for-pr`; the architect's design for #1454 declares three AGENTS.md edits (a §6g sentence naming the gate, the §6b `qa-validate.yml` bullet naming the step, and a §8 guard row), and a headless leg is REFUSED the write to that protected agent-instruction file (rule 3c)
- **Why:** an undeclared owed row vanishes — either the PR goes red on an unticked box, or the rulebook keeps describing the pre-gate behaviour while the pipeline enforces something else, so the rule 6g duty stops being readable from the rulebook
- **Done when:** an attended run lands the §6g sentence, the §6b bullet and the §8 guard row from this ledger issue
- **Owed-row:** <!-- owed-row: section=8 needle="make findings-check-for-pr" -->
