# Publishing the agent image is a deliberate, guarded act

**Issue:** [#206](https://github.com/andyholst/trending-local-llms/issues/206)
**Capability:** `agent-image` (extends the change of issue #207)

## Why

The base image **is** the agent image — it bakes the Hermes CLI and the pinned
`keeltrace/hermes-nerve` plugin, and every bot job (`hermes-smoke`,
`implement-issue`, `review-issue`, the fix loop) runs inside it. Publishing it is
therefore a privileged act over the toolchain the whole fleet trusts. Here it was
not an act at all: the only publisher was `refresh-bot`'s `build` job, so

1. **"Republish the toolchain" and "refresh the data" were one switch** — the only
   way to rebuild the image was `force_rebuild: true` on `refresh-bot`, which also
   runs the four search legs, the aggregate and the generated PR;
2. **nothing proved the credential before the build** — the job is budgeted 20
   minutes, the push happens at the end, and a token that cannot create the package
   failed *after* the build. llgenie measured exactly that on its own agent image
   (`denied: permission_denied: The token provided does not match expected scopes`,
   fixed by adding a push probe before the build — their PR #267);
3. **the cost was paid on every PR.** Measured on #220 (which does **not** touch
   the `Dockerfile`): `validate` ran `docker build -t trending-local-llms:latest .`
   — the bulk of the job's 9m31s, re-downloading Hermes — because no run had ever
   published this revision's `dockerfile-<sha12>` tag. The #207 PR paid 12m38s for
   the same reason.

## What Changes

- **`scripts/ensure_image.py` gains the publish path** (the script that already
  owns the tags — one implementation, rule 6d):
  - `ref` — print this revision's `dockerfile-<sha12>` tag and the `:latest` ref the
    fleet pulls;
  - `push-check` — prove the credential can write the package by **starting an
    empty blob upload** (`POST /v2/<path>/blobs/uploads/`), which the registry
    authorises exactly like a push; on refusal it repeats the registry's own words
    and says the build was NOT started. Nothing is uploaded and nothing is created
    for a credential that may not create;
  - `publish [--force]` — build + push **only when the hash tag is absent**, both
    the hash tag and `:latest`, so this publisher and `refresh-bot`'s `build` job
    cannot disagree about what is current.
- **`Makefile`**: `agent-image-ref`, `agent-image-push-check`,
  `publish-agent-image` (`FORCE=1` for the same inputs).
- **`.github/workflows/publish-agent-image.yml`** — `workflow_dispatch` **only**
  (no `schedule`, no `pull_request`, no `push`, no `workflow_run`), permissions
  `contents: read` + `packages: write`, `concurrency: publish-agent-image`
  (`cancel-in-progress: false`), and the same owner/collaborator **`guard` first,
  before any secret**, requiring both `github.actor` and `github.triggering_actor`
  to be the owner or a collaborator with `admin|maintain|write`. The publish job
  logs in with the **default `GITHUB_TOKEN`** (as the triggering actor), runs
  `make agent-image-push-check` **before** `make publish-agent-image`, and prints
  the refs. It never merges and never pushes a branch.
- **`tests/test_publish_agent_image.py`** — the script's modes run for real with the
  `docker` CLI faked (the harness `tests/test_ensure_image.py` already uses) and,
  for the probe, a **local HTTP server** standing in for the registry: the
  no-op-when-published path, both refs pushed when absent, `--force`, the refusal
  reported verbatim, no credential named, and the workflow's shape (dispatch-only,
  guard first, default token, probe before build, no merge).
- **`ARCHITECTURE.md`** gains the pipeline (every job of it), the three targets and
  the base row's second publisher; the README bullet on the runner images names the
  deliberate publish (through its template in `scripts/update_trending.py`).

## Not covered

- **`AGENTS.md`**: this change *should* extend rule 6k with clause (c) (publishing
  is deliberate and guarded) plus a section-8 guard row. The file is protected and
  the write was not approved, so it is **not** in this change — it needs the owner's
  explicit approval and is called out in the PR body.
- `refresh-bot`'s own `build` job stays as it is: this adds a door, it does not move
  the existing one. Consolidating the two publishers is a follow-up.
- The rebuild *decision* that lives as inline shell in `refresh-bot.yml` —
  [#208](https://github.com/andyholst/trending-local-llms/issues/208).
