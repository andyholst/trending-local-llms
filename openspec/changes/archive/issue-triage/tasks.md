## 1. The input

- [x] 1. `scripts/issue_thread.py` + `make issue-thread` render the whole thread (title, body, every comment oldest-first with author + ISO8601Z, then the decision instruction); no comments is said in words, an unreadable issue exits 2

## 2. The verdict

- [x] 2. `scripts/issue_verdict.py` + `make issue-verdict` apply the verdict deterministically: `implement` writes nothing, `refine` posts ONE restatement + `agent:refined`, `close` posts the reason with its cited EVIDENCE, closes and applies `agent:closed`
- [x] 3. The refusals are loud (exit 2, nothing written): close with no EVIDENCE, refine with no restatement, missing/unknown TRIAGE, missing file
- [x] 4. The label is re-read after applying it and its absence is fatal (the #161 lesson: `--add-label` can exit 0 having applied nothing)

## 3. The queue and the pipeline

- [x] 5. `agent:refined` / `agent:closed` are a hold in the SHARED queue rule (`scripts/issue_queue.py`), reported as `reason=decided:<label>` with no TTL — no second copy of the rule in shell
- [x] 6. The workflow renders the thread through `make issue-thread`, runs `make issue-verdict` under `set -o pipefail`, and gates the push / PR / fix loop / outcome comment / red step on `verdict == 'implement'`, so a refine or a close is GREEN with no PR
- [x] 7. The prompt requires `triage.md`, states the grammar, and scopes the gates it used to run to `TRIAGE: implement`; `triage.md` is gitignored and excluded from the commit

## 4. The record (rules 6b/6c/6d/6f/6h)

- [x] 8. `tests/test_issue_triage.py` locks the thread render, the three outcomes, the four refusals, the verified label and the wiring; the decided-hold case lives in `tests/test_issue_review.py`; both run in `make test`
- [x] 9. `ARCHITECTURE.md` (the two targets, the decided hold, the implementer row, the two scripts) and the README (through its template) describe the triage
- [x] 10. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`, `make lint` and `make secret-scan` are green on the branch
