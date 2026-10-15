## 1. The publish path in the one script

- [x] 1. `scripts/ensure_image.py` gains `ref` (this revision's hash tag + the consumer `:latest` ref), `push-check` (an empty blob upload; the registry's refusal verbatim; "the build was NOT started"; a loud failure with no credential) and `publish [--force]` (build + push ONLY when the hash tag is absent; pushes both refs)
- [x] 2. `Makefile`: `agent-image-ref`, `agent-image-push-check`, `publish-agent-image` (`FORCE=1`) — all three through the one script (rule 6d)

## 2. The pipeline

- [x] 3. `.github/workflows/publish-agent-image.yml`: `workflow_dispatch` only; `permissions: contents: read` + `packages: write`; `concurrency: publish-agent-image` with `cancel-in-progress: false`
- [x] 4. Its `guard` job runs FIRST, before any secret, requiring both `github.actor` and `github.triggering_actor` to be the owner or a collaborator with `admin|maintain|write`
- [x] 5. Its `publish` job (`needs: guard`) logs in with the default `GITHUB_TOKEN` as the triggering actor, runs `make agent-image-push-check` BEFORE `make publish-agent-image`, honours a `force` input, prints the refs, and never merges or pushes a branch

## 3. The record (rules 6c/6d/6f/6h)

- [x] 6. `tests/test_publish_agent_image.py` locks the script's modes (no-op when published, both refs when absent, `--force`, the probe's refusal and its missing-credential path against a local HTTP server) and the workflow's shape (dispatch-only, guard first, default token, probe before build, no merge), and is wired into `make test`
- [x] 7. `ARCHITECTURE.md` describes the pipeline, the three targets and the base image's second publisher; the README bullet names the deliberate publish (through its template)
- [x] 8. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`, `make lint` and `make secret-scan` are green on the branch, and the probe is exercised against the real registry (a refusal is a valid result: it must fail fast, before any build)
