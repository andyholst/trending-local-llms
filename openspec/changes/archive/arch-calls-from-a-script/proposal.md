# A target reached through a shell script is described

**Issue:** [#482](https://github.com/andyholst/trending-local-llms/issues/482)
**Capability:** `architecture-inventory`

## Why

The generated block lists `fix-bot.yml`'s calls as `image-ensure`, `hermes-smoke`,
`git-identity` — but that job's real work is `scripts/fix_loop.sh`, which runs `make lint`,
`make validate-search`, `make validate-mapped`, `make openspec-check`, `make architecture-check`,
`make test` and `make fix` itself. `workflow_targets` reads a workflow's `run:` bodies, so a target
invoked one level down is never reported. Stating three targets for a job that runs eight is a
description that quietly misleads, and following the shell by parsing it would be the guesswork the
block exists to avoid.

## What Changes

- **A declaration, not a guess.** A script may carry `# arch-calls: <target> …`; the generator reads
  it **only for the scripts a step actually runs**, and reports those targets as calls of that step.
- **The declaration is checked.** `_arch_calls_problems` refuses a declared target the Makefile does
  not define, at BOTH the write and the check path — so a stale entry fails
  `make architecture-check` instead of describing a call that no longer exists.
- **`scripts/fix_loop.sh`** declares the eight targets it runs.
- **The declaration is not the script's description**: `script_lines` skips an `arch-calls:` line
  when picking the one-line role, so machine data never lands where a reader expects a purpose.
- **`tests/test_architecture_bot.py`** — a fixture workflow whose step runs a declaring script: the
  targets are reported for that workflow, a declaration naming a `ghost-target` is refused, and the
  ghost is never rendered.

## Impact

`fix-bot.yml`'s line in §10 now names what the job really runs. Any future script that shells out to
`make` can declare its targets and be described accurately, or fail the check if it lies.

## Not covered (out of scope)

- Only a script named DIRECTLY in a `run:` body is followed; a script invoked by another script
  still needs its own declaration, and a chain two deep is not walked. Filed as a finding.
