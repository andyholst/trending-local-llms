# Proposal: provision-fleet-profile-homes

Issue: #1142 — "fleet: no seam provisions a rendered lane config into the Hermes profile home
that runs it, so the chain is green in the repo and wrong on the machine"
PR: (this change)

## Why

Issue #1140 gave the fleet a model chain (`agents/model_chain.json`) and a renderer
(`make agent-profile-model-render` → `agents/tll-<lane>/config.yaml`), and
`make agent-model-chain-check` (bundled into `make lint`) refuses a lane config that drifted from
the chain. That half is green. The half nobody built is the OTHER side of the arrow — nothing
copies the rendered config into the Hermes profile home that actually RUNS a lane:

- `grep -rn "profiles/" Makefile scripts/*.py .github/workflows/*.yml` finds no code path that
  writes a profile home (measured on `origin/master` in issue #1142): the only profile-home writes
  in the tree are the `agents/skills` copies in the `_setup` recipe, and the `Makefile` never names
  `~/.hermes/profiles`.
- On the machine that runs the lanes, the seven `~/.hermes/profiles/tll-*/config.yaml` still read
  `provider: strata` / `default: qwen3.8-flash-next-q2_0` /
  `base_url: http://127.0.0.1:8080/v1` / `key_env: HERMES_CUSTOM_127_0_0_1_8080_API_KEY` — the
  exact hand-materialised shape #1140 measured and reported — while `make agent-model-chain-check`
  exits green and `make agent-profile-model-render` refreshes only the repository copies.
- `printenv | grep -c NOUS_API_KEY` printed `0` on that machine (issue #1142): the chain names
  `key_env: NOUS_API_KEY`, so a lane provisioned from it there would be a keyless lane, failing
  inside a model call rather than at a gate (the §3e / §6k story: a missing credential surfaces as
  a 401/403 deep inside a bot run, after the expensive leg has already started).

"Green in the repo, wrong on the machine" is a defect the repo cannot see: every gate reads the
tree, and the tree is not where a lane runs.

## What Changes

- `scripts/agent_profile_provision.py` — the ONE provisioning seam (rule 6d): lanes come from
  `agent_model_chain.fleet_lanes` (derived from `agents/tll-*/SOUL.md`, never a hand-kept list),
  the bytes written are `agent_model_chain.render_text`'s output, and the credential check is
  `scripts/require_env.py` (the ONE pre-flight, issue #357). It copies
  `agents/tll-<lane>/config.yaml` to `<profiles-home>/tll-<lane>/config.yaml`, and it REFUSES
  (exit 2, naming what it refused, writing nothing) when: the credential a chain `key_env` names is
  absent; a lane config on disk is not what the chain renders (a live home must never receive what
  `agent-model-chain-check` would red); the chain is unreadable; a named lane is not in the fleet;
  or nothing was named (writing a live profile home is never a default).
- Rule 3b additive: a home's existing `config.yaml` is never destroyed — it is kept beside the new
  file as `config.yaml.bak-<UTC>`, so restoring a prior profile is a human act, never a side effect
  of an agent run.
- Rule 3e credentials-by-name: the seam reads only whether the named variable is SET and prints
  only NAMES; no value is read, printed or measured. `--dry-run` proves the chain, the credential
  and every lane config and writes nothing.
- `Makefile`: `_agent-profile-provision` (the seam) + `agent-profile-provision` (public,
  `LANE=<lane>` / `ALL=1` / `PROFILES_HOME=<dir>`, rule 6d).
- `qa-validate.yml` `live-smoke`: one step runs
  `make agent-profile-provision ALL=1 PROFILES_HOME="$RUNNER_TEMP/hermes-profiles"` so the seam is
  executed by the pipeline and not only by a human (rule 6m), against a runner temp home so a CI
  run never writes a real profile home.
- `tests/test_agent_profile_provision.py` — 37 assertions, standalone module, discovered by
  `make test`, running the real seam against a scratch tree and a scratch profile home (the only
  external system is the filesystem, rule 6m).

## Impact

- Affected specs: `fleet-profile-provision` (new capability)
- Affected code: `scripts/agent_profile_provision.py` (new), `Makefile` (2 targets),
  `.github/workflows/qa-validate.yml` (1 live-smoke step), `tests/test_agent_profile_provision.py`
  (new), `ARCHITECTURE.md` (target + script rows)
- Affected tests: `make test` gains the module; `qa-validate`'s `live-smoke` job gains the target

## Not covered

- It does NOT write the credential or install the fleet (that stays an operator act, rule 3e: only
  the NAME arrives). It does NOT decide WHICH profile home a human's machine uses — the default is
  Hermes's own `~/.hermes/profiles`, overridable by `PROFILES_HOME` / `HERMES_PROFILES_HOME`.
- It does NOT change `agents/model_chain.json`, the renderer, or `agent-model-chain-check`: the
  chain and its gate stay the single source this seam copies from (rule 6d).
- It does NOT delete a backup or rewrite a profile home it did not provision.
