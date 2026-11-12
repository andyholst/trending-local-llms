# Tasks: per-round-log-capture (#631)

- [x] `scripts/scrub_log.py`: `stream(append=…)` + `--append` flag; each
  appended invocation opens both captures with a timestamped, pid-stamped
  `===== [scrub-log] capture … =====` delimiter (no delimiter imposed on a
  plain truncating invocation).
- [x] `Makefile` `scrubbed_run` seam passes `--append` (one seam: `make fix`,
  `make search-*`, `make implement-issue`, `make review-issue` all append).
- [x] `tests/test_scrub_log.py`: drive the REAL seam twice through a fixture
  Makefile — both transcripts survive in both captures, two delimiters, the
  planted value appears in NO redacted line, the failing round keeps its
  status; plus append-vs-truncate semantics test.
- [x] `tests/test_scrub_log.py` wiring test extended: the shipped
  `issue-bot.yml` QA artifact names `hermes-run.scrubbed.log` and no raw
  capture.
- [x] `.github/workflows/issue-bot.yml`: upload `hermes-run.scrubbed.log`
  with the QA artifact (redacted only).
- [x] `AGENTS.md` §3d sentence + §8 guard-table row (rule 3c/6c).
- [x] `ARCHITECTURE.md` refreshed (`make architecture-refresh`) and
  `make architecture-check` green.
- [x] `make openspec-check`, `make lint`, `make test` green in this branch.
