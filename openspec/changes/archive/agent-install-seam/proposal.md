# The agent image installs its agent through a seam, and proves it at build time

**Issue:** [#207](https://github.com/andyholst/trending-local-llms/issues/207)
**Capability:** `agent-image`

## Why

The base `Dockerfile` **is** the agent image — it bakes the Hermes CLI and the
pinned `keeltrace/hermes-nerve` plugin, and every bot job runs inside it. Two
things about it were taken on faith:

1. **The install was an `ADD <url>`.** `ADD https://hermes-agent.nousresearch.com/install.sh`
   cannot be overridden by a build arg, so a maintainer could not pin a version or
   point at a mirror without editing the Dockerfile, and a moved installer failed
   as an opaque fetch error. `make _setup` carried a *second*, curl-pipe-bash
   installer — two implementations of one stage.
2. **The build proved nothing about routing.** The `RUN` ended at
   `hermes --version`; the model alias the bots actually call was written only at
   run time by `make _setup`. A wrong model pin, a provider that is not `custom`
   or a `key_env` that is not `NOUS_API_KEY` was therefore discovered *inside a
   bot run*, after the image was published. This repo has already paid for that:
   with no alias, Hermes auto-routed to whatever key was in the environment and
   died with `HTTP 403` (`HF_TOKEN` → Hugging Face, measured on the first
   issue-bot run, #124).

`asimov-agent/llgenie` solved both for its own agent image (`containers/agent/Dockerfile`,
`scripts/install_hermes_ci.sh`, issue #238) and asserts the alias at build time so
*a bad pin fails the BUILD, not later, inside a bot run*.

## What Changes

- **`scripts/install_hermes_ci.sh`** — the ONE installer seam, used by the image
  build and by `make _setup`: an existing `hermes` on PATH → `HERMES_INSTALL_URL`
  → `uv tool install $HERMES_PACKAGE` → **fail loudly**, naming all three paths
  tried. It never reads or writes a credential (the key arrives at run time as
  `-e NOUS_API_KEY`, rule 3e).
- **`Dockerfile`** — `ARG HERMES_INSTALL_URL` / `ARG HERMES_PACKAGE` carry the pin
  visibly (overridable without editing the file); the `ADD` is gone; after
  `COPY . .` the build runs `make _setup` and then `make _hermes-alias-check`, so a
  wrong pin fails the build.
- **`Makefile`** — `HERMES_ALIAS` (one definition of the alias name, used by the
  writer and the reader), `HERMES_INSTALL_URL` / `HERMES_PACKAGE` with the live
  defaults, `_setup` routed through the seam, and a new `_hermes-alias-check`
  recipe (internal) with the public `hermes-alias-check` wrapper. The check
  reports **every** mismatch, not just the first.
- **`tests/test_install_hermes_ci.py`** — the seam's four branches (present CLI,
  URL installer, installer that produces nothing → `uv`, nothing works), the
  credential rule, the Dockerfile's shape (seam, build args, assertion order, no
  key value), the pin having one value across the two files, the alias having one
  name for writer and reader, and the real `_hermes-alias-check` going green on the
  pin and red on a different provider. Wired into `make test`.
- **`ARCHITECTURE.md`** gains the two properties and the new target (rule 6h);
  **`AGENTS.md`** gains rule 6k and its section 8 row; the README bullet on the
  runner images says the image proves its agent.

## Not covered

- Publishing the agent image deliberately, behind its own guard and a push check —
  [#206](https://github.com/andyholst/trending-local-llms/issues/206).
- Moving `refresh-bot.yml`'s inline rebuild decision into a tested unit —
  [#208](https://github.com/andyholst/trending-local-llms/issues/208).
- `make hermes-smoke` skipping when `NOUS_API_KEY` is unset —
  [#209](https://github.com/andyholst/trending-local-llms/issues/209).
- The base image's missing `gh` — already [#194](https://github.com/andyholst/trending-local-llms/issues/194).
