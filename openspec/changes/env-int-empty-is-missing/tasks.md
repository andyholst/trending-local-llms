# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. Reproduced the failure at both layers: `MAX_FIXBOT_COMMITS= python3 scripts/pr_health.py` and the real `make pr-health REPO=… COMMENT=1` (ValueError, exit 2)
- [x] 3. `scripts/env_int.py`: `env_int` / `env_float`, unset or blank → default, non-numeric → `EnvSettingError` naming the variable
- [x] 4. Every `int(os.environ…)` / `float(os.environ…)` in `scripts/` converted (pr_health, issue_queue ×3, issue_review, ensure_image ×2, validate ×2, verify_closure ×2)
- [x] 5. `Makefile`: `pr-health` forwards `MAX_FIXBOT_COMMITS` only when set
- [x] 6. Tests: the truth table, the REAL `make pr-health … COMMENT=1` with a stub `gh`, the bare-read guard, the Makefile assertion
- [x] 7. Proven to bite: 6 of the new checks FAIL against the pre-change sources; 45/45 pass after
- [x] 8. `AGENTS.md` §8 row for the new guard (rule 6c); `ARCHITECTURE.md` §10 regenerated so the new script is described (rule 6h)
- [x] 9. `OPENSPEC.md` regenerated; `make openspec-check`, `make lint`, `make architecture-check`, `make test`, `make validate-mapped` run
- [x] 10. `findings.md` written
