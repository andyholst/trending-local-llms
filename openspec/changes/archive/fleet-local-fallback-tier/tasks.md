# Tasks — fleet-local-fallback-tier (issue #1192)

- [x] Re-read the live Nous free tier (`GET /v1/models`, 2026-11-21T12:26:21Z: 415 models, 5 `:free`, ids unchanged) and the local box (`GET http://127.0.0.1:8080/v1/models`: `qwen3.8-flash-next-iq3_xxs`, ctx 131072); record both in the chain's `measured` block
- [x] Add the credential-less `local_fallback` entry to `agents/model_chain.json` (additive: every existing entry kept; `previous_read` preserved)
- [x] Extend `scripts/agent_model_chain.py`: role, bare-id regex, per-row provider/base_url, local-tier refusals, key_env skip, render (alias block + `fallback_providers` order), report width
- [x] Extend `scripts/agent_profile_provision.py`: `--profile` merge (owned blocks only, byte-verified, idempotent), `default`, lane-via-profile and missing-home refusals
- [x] Wire `PROFILE=` comma list through the Makefile (`comma := ,`, per-name `--profile`); prove expansion with `make -n`
- [x] `make agent-profile-model-render && make agent-model-chain-report && make agent-model-chain-check` green (7 lanes, order free-longcat -> free-hy4 -> free-qwen4 -> free-solar -> free-step -> local-strata -> nous-deepseek)
- [x] Update `tests/test_agent_model_chain.py` (role partition fix, local-tier assertions, 9 refusal cases, runtime-order test) — PASSED 84 | FAILED 0
- [x] Update `tests/test_agent_profile_provision.py` (strata assertion, merge/default/refusal guards, PROFILE wiring) — PASSED 54 | FAILED 0
- [x] Rule 6c red-on-old-seam proof: `git show origin/master:scripts/agent_model_chain.py --check` over the new chain exits 1 (`role 'local_fallback' is not one of …`, bare id refused); the old provision seam cannot merge a profile
- [x] OpenSpec change: proposal, capability spec with Test lines, this checklist
- [x] `findings.md` written and `make findings-check` green; findings filed (`make file-findings` → #1194 strata chat hang, #1195 weekly free-model refresh pipeline, #1196 durable NOUS_API_KEY)
- [x] ARCHITECTURE.md §6 rows true + `make architecture-refresh` (§10 docstring staleness); AGENTS.md §8 row updated (rule 3c attended sign-off, comment on #1192)
- [x] `make lint` green (chain check, architecture check, workflow guards, linefeeds)
- [~] Full suite (`make test`) green on the PR head — blocked: qa-validate runs it after push; on the host the two affected modules are green (84 + 55 checks, 0 failures) and every new refusal was proved red on the pre-change seam
- [x] `make openspec-check` green (index regenerated, binding, backlog)
- [x] Provision every host home from the rendered chain: `make agent-profile-provision ALL=1 PROFILE=<22 non-lane homes>,default` with `NOUS_API_KEY` exported by NAME — 7 lanes + 23 merges, 30 backups kept; read-back verified all 30 homes carry the rendered `model:`/`model_aliases:`/`fallback_providers:` blocks byte-for-byte with the free primary as default
- [x] PR opened (#1197, five-section body, single `closes #1192`), `make pr-message-check` green, `make openspec-record-pr ISSUE=1192 PR=1197` so the archive sits at the PR head
