# Proposal: fleet-tll-fleet-profile-model-chain

Issue: #1140 — "fleet: give every provisioned tll-* profile its own config.yaml with the
PR: #1141
free-model chain first and deepseek-v4-flash-0731 last"

## Why

The host fleet is seven lanes under `agents/` (`tll-architect`, `tll-implementer`, `tll-planner`,
`tll-pr-rebase`, `tll-reviewer`, `tll-security`, `tll-tester`), and NOTHING in the tree decides
which model a lane runs:

- the repo pins ONE paid model for every agent leg — `HERMES_MODEL := deepseek/deepseek-v4-flash-0731`
  (`Makefile:102`), alias `nous-deepseek` (`Makefile:107`), priced
  `5.4e-8 / 1.62e-7` per prompt/completion token;
- no `agents/tll-*/config.yaml` is tracked on `master` (`git ls-tree origin/master` names only each
  lane's `SOUL.md` and skills), so a lane's model is invisible to every gate in the repo;
- the provisioned profile homes on this host (`~/.hermes/profiles/tll-*/config.yaml`) were each
  materialised by hand and all seven read `provider: strata` / `default: qwen3.8-flash-next-q2_0`
  with `key_env: HERMES_CUSTOM_127_0_0_1_8080_API_KEY` — a model and a credential name the fleet's
  own pipelines never forward (they forward `NOUS_API_KEY`, rule 3e), and no free-model step at all;
- the Nous Portal serves five models at pricing 0 today — measured live from
  `https://inference-api.nousresearch.com/v1/models` on 2026-11-19 (`/tmp/nous_models.json`,
  413 models, exactly 5 with pricing 0): `meituan/longcat-2.5:free` (1,048,576 ctx),
  `tencent/hy4-flash:free` (1,048,576), `qwen/qwen4-max:free` (1,000,000),
  `upstage/solar-mini4:free` (524,288), `stepfun/step-3.7-flash:free` (262,144).

A fleet with no declared chain burns paid tokens for work the free tier can do, and an operator who
hand-edits one lane's config has no gate that can notice the lane drifted.

## What Changes

- `agents/model_chain.json` — the ONE source of the fleet model chain: `primary`
  `meituan/longcat-2.5:free`, then the four other free models in list order as `fallback`s, then
  the Makefile-pinned model (`HERMES_MODEL` / `HERMES_ALIAS`) as the single paid `last_resort`;
  each step carries its alias, provider, `base_url`, `context_window` (the measured figures) and
  `key_env: NOUS_API_KEY` — a NAME only, never a value. The file states where its model ids were
  measured (rule 2).
- `scripts/agent_model_chain.py` — the ONE seam (rule 6d): `--write` renders each lane's
  `agents/<lane>/config.yaml` (`model:` block + `model.aliases.*`) from the chain; `--check`
  refuses a config that drifted from the chain (naming the lane, the line and both spellings), a
  chain that lost its shape (two primaries, no fallback, no last resort, a paid step ordered before
  a free one, one alias twice), a `last_resort` whose model or alias is not the Makefile pin, a lane
  whose config was never rendered, and any credential ASSIGNMENT in either file; an unreadable or
  missing chain is exit 2 `UNDECIDABLE`. `--report` prints the chain in the order it is used.
  Lanes are DERIVED from the tree (`agents/tll-*/SOUL.md`), never a hand-kept list.
- `Makefile`: `_agent-profile-model-render` / `agent-profile-model-render` (the repair half),
  `_agent-model-chain-check` / `agent-model-chain-check` and `_agent-model-chain-report` /
  `agent-model-chain-report` (rule 6d), `agent-model-chain-check` bundled into `make lint` — the
  first gate of `qa-validate`'s `validate` job and the first check of `scripts/fix_loop.sh` — and
  `DOCKER_RUN`/`TEST_RUN` forward `NOUS_API_KEY` by NAME so a lane is never keyless (rule 3e).
- `agents/tll-*/config.yaml`: the seven lane configs are now tracked and RENDERED from the chain
  (all seven carry the same chain, `key_env: NOUS_API_KEY`).
- `tests/test_agent_model_chain.py`: the behavioural guard — 10 tests, standalone module, wired
  through `make test`.

## Impact

- `make lint` refuses a hand-edited lane config, so fleet model drift blocks auto-merge instead of
  surfacing as a gateway error inside a run.
- Free-first by construction: a lane's first step is a `:free` model and the paid
  `deepseek/deepseek-v4-flash-0731` is reachable only as the last step.
- A Portal price/tier change is a one-file edit to `agents/model_chain.json` plus
  `make agent-profile-model-render` — never seven hand-edited configs.
- Rule 3e becomes mechanically checkable for the fleet: the renderer only ever writes `key_env`.
- No data, README, search, validator, workflow or merge-gate behaviour changes besides the new
  `make lint` check.

## Not covered

- Materialising the rendered config into `~/.hermes/profiles/tll-<lane>/config.yaml` is the
  provisioning seam of issues #762/#763 (`make sync-agent-profile` / `make provision-agent-profiles`
  do not exist on `master` yet); this change lands the repo-side single source and gate, and the
  rendered `agents/<lane>/config.yaml` is the artifact such a seam copies. The existing hand-written
  profile homes are NOT rewritten by this change.
- The lanes' `SOUL.md` task prompts, skills and cadence (unchanged — `fleet-cadence` /
  `host-fleet` capabilities).
- Per-lane model *overrides*: the chain is global by design; giving one lane a different cost
  profile is a contract decision on issue #1140, not a hand edit of a generated file.
- The live profile homes' own `api_key: ${HERMES_CUSTOM_127_0_0_1_8080_API_KEY}` spelling — outside
  the repository, so `make agent-model-chain-check` cannot see it; rule 3e is enforced on the tree.
