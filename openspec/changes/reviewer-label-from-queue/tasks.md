# Tasks

- [ ] 1. The failing guard exists first: a scripts-wide literal scan + `LABEL`/`decide()` derivation check in `tests/test_issue_review.py` goes RED on the three-copy code
- [ ] 2. `scripts/issue_review.py::decide()` asks `iq.QUEUE_LABELS[0]`, not a literal
- [ ] 3. `scripts/data_gap_analysis.py::LABEL` is derived from `issue_queue.QUEUE_LABELS[0]`
- [ ] 4. The guard is green locally and its §8 row lands in AGENTS.md in the same change (rule 6c)
