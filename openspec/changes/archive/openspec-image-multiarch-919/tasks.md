# Tasks: openspec-image-multiarch-919

- [x] 1. `scripts/openspec_manifest_check.py` — `docker manifest inspect` verdict: exit 1 when
      the published manifest lacks arm64 (or amd64), exit 2 when it cannot be read or the tag
      is missing
- [x] 2. `refresh-bot.yml`: `platforms: [linux/amd64, linux/arm64]` on the openspec-image
      build-push step, and `make openspec-manifest-check` after publish AND on the
      skip-rebuild branch
- [x] 3. `openspec/Dockerfile` comment recording the multi-arch contract (the content hash
      changes, so the next refresh publishes the multi-arch tag)
- [x] 4. `Makefile`: `openspec-manifest-check` target (`$(PYTHON_RUN)`) + `.PHONY`
- [x] 5. `tests/test_openspec_manifest_check.py` — stubbed `docker` (external system only,
      rule 6m): amd64-only red, multi-arch green, unreadable exit 2, missing tag exit 2,
      the real workflow pinned (platforms + both verify paths + Makefile-only wiring)
- [x] 6. `AGENTS.md` §6f sentence (rule-3c diff declared in a comment on issue #919)
- [x] 7. `ARCHITECTURE.md` rows + `make architecture-refresh`; `make lint`,
      `make secret-scan`, `make openspec-check` green
