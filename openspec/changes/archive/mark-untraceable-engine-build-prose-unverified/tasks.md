# Tasks

- [x] 1. `data/models.json`: the five flagged rows (`bonsai-2-9b-apple-silicon-yukon`, `qwen2.5-0.5b`, `qwen3-8-flash-next-125b`, `gemma-4-e4b`, `qwen3.8-27b-r9700-vllm-dflash2-w4a16`) gain a model-level `engine_min_version` distilled from the row's own text with the `(est)` marker — additive only (rule 3b). Verified: `make validate-data` QA PASSED; `make data-gaps` shows the untraceable `engine_min_version` line gone and 14 re-askable declared estimates.
- [x] 2. `tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text`: marked estimates exempted from the evidence and post-URL checks; two new boundary checks pin that an UNmarked invented value is not exempted and a marked one is.
- [x] 3. New guard `test_untraceable_engine_build_prose_is_declared_unverified_in_the_store`: empty untraceable class on the shipped store, five marked rows, report names them as declared estimates, none reappears `unstructured`. Verified: `python3 tests/test_data_gap_analysis.py` PASSED 306 | FAILED 0.
- [x] 4. `AGENTS.md` §8: the guard row for the class-emptying store gate.
- [x] 5. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 6. `findings.md` written and `make findings-check` green.
- [x] 7. Gates green: `make lint`, `make test`, `make validate`, `make architecture-check`, `make openspec-check` (incl. backlog/binding), `make secret-scan`.
