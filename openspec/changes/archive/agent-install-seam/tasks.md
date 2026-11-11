## 1. The seam

- [x] 1. `scripts/install_hermes_ci.sh` installs through one path (already installed → `HERMES_INSTALL_URL` → `uv tool install`) and fails loudly, naming every path it tried, when none works
- [x] 2. The seam never reads, writes or forwards a credential; `_setup` runs the same seam (no second curl-pipe-bash installer)
- [x] 3. `Dockerfile`: `ARG HERMES_INSTALL_URL` / `ARG HERMES_PACKAGE` carry the pin, the `ADD <url>` is gone, and the install goes through the seam

## 2. The build-time proof

- [x] 4. The build runs `make _setup` and then `make _hermes-alias-check`, which reads every `model.aliases.$(HERMES_ALIAS).*` field back and fails the BUILD on a mismatch (reporting every mismatch)
- [x] 5. `HERMES_ALIAS` is defined once and used by both the writer (`_setup`) and the reader (`_hermes-alias-check`); the public `hermes-alias-check` wrapper exists
- [x] 6. Every existing test still passes with `_setup` writing `model.aliases.$(HERMES_ALIAS).*`

## 3. The record (rules 6c/6d/6f/6h)

- [x] 7. `tests/test_install_hermes_ci.py` locks the four seam branches, the credential rule, the Dockerfile shape, the shared pin, the shared alias name and the green/red alias check; it is wired into `make test`
- [x] 8. `ARCHITECTURE.md` describes the seam, the build-time assertion and `hermes-alias-check`; `AGENTS.md` gains rule 6k and its section 8 row; the README bullet names the proof
- [x] 9. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`, `make lint` and `make secret-scan` are green on the branch, and the base image builds (the build itself runs the seam and the assertion)
