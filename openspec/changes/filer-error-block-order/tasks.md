# Tasks: filer-error-block-order

- [ ] `scripts/pipeline_failure_issue.py` — `extract_error_block` presents the failing-region lines
      first (log order), then strong shapes elsewhere, then soft chatter, with one explicit
      `[filer] … FILLER …` marker; cap, de-dupe, drop note and the ungrouped fallback unchanged.
- [ ] `tests/test_pipeline_failure_issue.py` — both directions locked: a thin region with earlier
      chatter emits the diagnosis first; a region holding the diagnosis keeps today's order.
- [ ] `tests/test_pipeline_failure_error_block.py` — the whole-block "keeps log order" assertion
      becomes the per-group contract (region first, filler after a marker).
- [ ] `AGENTS.md` §6r + §8 — the presentation sentence and the guard row (rule 3c, attended
      sign-off on this PR).
- [ ] Refresh `OPENSPEC.md`; `make openspec-check` green.
- [ ] `findings.md` analysis, `make lint`, and the focused modules via their own `main()`.
