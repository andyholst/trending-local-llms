## 1. The two checks

- [x] 1. `scripts/hermes_smoke.sh` FAILS, non-zero, when `NOUS_API_KEY` is unset — naming the variable, the `nous-deepseek` alias whose routing could not be proven, and the consequence of a green result here; it never calls `hermes`
- [x] 2. `scripts/model_caps_check.py` FAILS, non-zero, on the same input — naming the variable and that the model id, its real `max_completion_tokens` and its `reasoning` support stay unverified
- [x] 3. One explicit, non-default opt-out on both (`LIVE_CHECK_ALLOW_UNCONFIGURED=1` → `NOT CONFIGURED` + exit 0), documented in each script's header

## 2. The record (rules 6c/6d/6f/6h)

- [x] 4. `tests/test_hermes_smoke.py` pins the failure (non-zero, names the variable and the alias, not a SKIP, `hermes` never called) and the opt-out path, replacing the case that locked the old SKIP
- [x] 5. `tests/test_search_budget.py` pins the same for `model_caps_check.py`, replacing its SKIP case
- [x] 6. A guard reads every `.github/workflows/*.yml` and fails if any sets `LIVE_CHECK_ALLOW_UNCONFIGURED` (CI holds the keys, so CI always proves)
- [x] 7. `ARCHITECTURE.md` describes the loud failure for `model-caps`, `hermes-smoke` and `pipeline-smoke`; the README bullet on key handling gains the same sentence (through its template); `AGENTS.md` gains the section 8 row
- [x] 8. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`, `make lint` and `make secret-scan` are green on the branch
