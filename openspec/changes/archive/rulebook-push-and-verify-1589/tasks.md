# Tasks: rulebook-push-and-verify-1589

- [x] Cut `rulebook-push-and-verify-1589` from freshly fetched `origin/master` (`972f82617a0b368ad7fd27e0776038fe31942b91`, measured this session; `0231f310`/`6e50fc25` were superseded while the lane waited on the protected write) in its own worktree
- [x] Land the §7b push-and-verify bullet verbatim from the reviewer verdict (issuecomment-7129333153)
- [x] Append the Rule 3c note clause for #1589 after the last clause on the landed head (#1258's; #1482 has not landed)
- [x] Land the §8 row for `tests/test_push_and_verify_guard.py` verbatim
- [x] Add `tests/test_push_and_verify_guard.py` — names-only pin, RED on base / GREEN on target verified by execution
- [x] Apply the three `AGENTS.md` hunks through the sanctioned file tool — landed after the owner-authorized #1591 config change (`security.protected_instruction_files: false`, announced in #issuecomment-7130207535)
- [x] Regenerate `OPENSPEC.md`; keep the OpenSpec checks green
- [x] Run the fast offline checks only; the containerised `make validate`, whole `make test` and `make live-smoke` stay CI-only
