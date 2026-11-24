# Tasks: filer-error-block-order

- [x] `scripts/pipeline_failure_issue.py` — `extract_error_block` presents the failing-region lines
      first (log order), then strong shapes elsewhere, then soft chatter, with one explicit
      `[filer] … FILLER …` marker; cap, de-dupe, drop note and the ungrouped fallback unchanged.
- [x] `tests/test_pipeline_failure_issue.py` — both directions locked: a thin region with earlier
      chatter emits the diagnosis first; a region holding the diagnosis keeps today's order.
- [x] `tests/test_pipeline_failure_error_block.py` — the whole-block "keeps log order" assertion
      becomes the per-group contract (region first, filler after a marker).
- [~] `AGENTS.md` §6r + §8 — the presentation sentence and the guard row — blocked: rule 3c human
      sign-off (AGENTS.md protected in a headless leg); declared on issue #1466, owed row recorded
      in `findings.md`
- [x] Refresh `OPENSPEC.md`; `make openspec-check` green.
- [x] `findings.md` analysis, `make lint`, and the focused modules via their own `main()`.
