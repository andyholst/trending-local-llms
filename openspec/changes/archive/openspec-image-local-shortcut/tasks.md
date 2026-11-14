# Tasks

- [x] 1. Proposal + capability spec for the OpenSpec CLI image seam's local reuse (#767).
- [x] 2. `scripts/ensure_image.py`: `openspec_ready()` (a `docker image inspect` of the exact hash tag) checked FIRST in `ensure_openspec` — local → tag onto `OPENSPEC_IMAGE`, zero registry calls; not local → the unchanged `published()` → pull → tag path; not published → build, tagging BOTH `OPENSPEC_IMAGE` and the exact hash tag.
- [x] 3. `tests/test_ensure_image.py`: stub gains a `FAKE_DOCKER_IMAGES` control so "published" and "present locally" are separate facts; new `test_ensure_openspec_present_locally_is_reused_without_a_pull` (no pull, no manifest inspect, no build when the tag is local — RED on the old seam); `test_openspec_image_is_hash_tagged_and_pulled_or_built` updated (pull path = published + NOT local; build path dual-tags).
- [x] 4. Verify the guard RED against the pre-change `scripts/ensure_image.py` (`git show origin/master:scripts/ensure_image.py`) and green against this change.
- [x] 5. `ARCHITECTURE.md` §6 row for `scripts/ensure_image.py` and the §"three runner images" text state the reuse rule; `AGENTS.md` §8 gains the guard row (rule 6c).
- [x] 6. Gates green: `make lint`, `make secret-scan`, `make test`, `make openspec-check` (arm64 host, NO `IMAGE_REPO` override, NO `DOCKER_DEFAULT_PLATFORM`), `make architecture-check`.
- [x] 7. `findings.md` + `make findings-check` / `make file-findings`: multi-arch publishing (#767's option 1) is this change's finding — filed as its own `tech-debt` issue.
- [x] 8. Commit (Asimov identity), push, open the PR via `make pr-title`/`make pr-body`, then `make openspec-record-pr ISSUE=767 PR=<n>` (records + archives) and push the archive.
