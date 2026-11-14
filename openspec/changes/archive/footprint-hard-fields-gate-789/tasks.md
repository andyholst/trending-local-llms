# Tasks: footprint-hard-fields-gate-789

- [x] OpenSpec change (proposal, MODIFIED spec with per-scenario tests, tasks)
- [x] `validate.py`: `_SOURCE_POST_GATE_FIELDS` / `_SOURCE_POST_REPORT_FIELDS` declared once;
      `_SOURCE_POST_FOOTPRINT` stays their union (rule 3b)
- [x] `check_source_post_readback`: hard-field flags become `data`-stage FAILURES (each
      attributed); prose flags stay WARN report-only with the reason
- [x] Stage registration relabelled `source-post readback (hard fields fail, prose report only)`
- [x] Tests: paired gate/report fixtures, per-hard-field coverage, field-split pin; the
      blanket "never fails" test retired
- [x] Live-store proof: the real scan over the shipped store flags 0 (gate lands green)
- [x] AGENTS.md §4/§8 rows updated to the split (rule 3c — diff names what changed)
- [x] Full local gates: `make lint`, `make secret-scan`, `make openspec-check`, `make openspec-index`
