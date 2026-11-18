# Tasks — #1120: the corrupt-tag fallback is silent on the PR that needed it

## Seam (the fallback becomes machine-readable)

- [x] `scripts/ensure_image.py` prints `corrupt-tag-fallback=<image>=<tag>` on each corrupt-tag fallback path (base / test / openspec) and appends it to `$IMAGE_FALLBACK_REPORT`; the pull / not-published / local-reuse paths print no such line
- [x] `scripts/bot_markers.py` registers the `corrupt-tag-fallback` marker (kind `image_fallback`, `qa-validate`), and `AGENTS.md` §6j names it in the same row (rule 6j)

## Announcer (ONE comment, never a second one)

- [x] `scripts/announce_image_fallback.py` composes the comment from the captured report (tag, reason, run URL), reads the PR thread with `--paginate` and skips when this run already announced, posts with `gh issue comment` on the default `github.token` (rule 6e), and exits 2 on missing inputs
- [x] `make announce-image-fallback` target wired (`PR=` `IMAGES=` `RUN_URL=`), and `master_alarm.GATES` names it so the target the validate job runs is registered (rule 6d)

## Pipeline wiring (no raw stream, no secret)

- [x] `qa-validate.yml`: `image-ensure` and `openspec-check` steps write ONE allowlisted `corrupt_fallback` key from the report FILE (no stream capture — rule 3f/#351), and a `pull_request`-only gated step calls `make announce-image-fallback` when either captured a fallback
- [x] `AGENTS.md` §8 carries the guard row naming what the tests catch (rules 6c/6h)
- [x] `ARCHITECTURE.md` describes the new target and the new script (target table + §6 row), and the generated inventory block was regenerated

## Tests

- [x] `tests/test_ensure_image.py` — the `$IMAGE_FALLBACK_REPORT` check (118 passed / 0 failed on this branch)
- [x] `tests/test_image_fallback_announce.py` (new; `gh` stubbed on PATH only — rule 6m) — 19 passed / 0 failed
- [x] `tests/test_workflows.py::test_the_corrupt_tag_fallback_is_announced_on_the_pr` — qa-validate pins
- [x] `tests/test_openspec_backlog.py` — 20 passed / 0 failed
- [~] the whole `make test` suite green on this branch — blocked: the suite is running on another branch of this machine at the time of writing; this branch re-runs it before the PR is armed
