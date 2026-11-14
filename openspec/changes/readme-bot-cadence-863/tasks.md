# Tasks: readme-bot-cadence-863

- [x] Render template fixed: weekly Wednesday sweep + backup slot, reviewer weekly, queued-alarm `37 * * * 3`, code-review `7 6 * * 3` — verified by the template scan test
- [ ] `README.md` regenerated via `make render-readme` — verified when `test_the_real_repo_readme_is_clean` passes
- [x] `check_readme_bot_cadence` added and registered in the readme stage (wiring test covers registration; the real check runs in the fixture tests)
- [x] `tests/test_readme_bot_cadence.py`: planted wrong shapes all refused, true weekly line passes, refusal not vacuous — 10/0
- [ ] Full local gates: `make lint`, `make secret-scan`, `make openspec-check`, new suite, `make validate --only readme` on the regenerated README
- [ ] PR opened with the five-section body and `closes #863` (never draft)
