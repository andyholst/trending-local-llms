# Proposal: refresh-fixture-generated-paths-1828

Issue: #1828
PR: #1829

## Why

Refresh run 46022812623 got every leg green, then `aggregate` failed twice. #1826 and #1827 cover the two test modules. The second failure is `Commit + open PR if changed`: `refresh-sync` refused the tree because `tests/fixtures/hermes_releases_latest.json` is not in `GENERATED_PATHS`, so no refresh PR opened and the store stayed dated 2026-11-17. The fixture is written by `make hermes-pin-channel-record`, which the refresh itself runs (issue #1163), so the allow-list drifted away from what a refresh writes — the #997 class recurring with a new path.

## What Changes

- Add `tests/fixtures/hermes_releases_latest.json` to `refresh_base.GENERATED_PATHS` so `sync` accepts a tree dirty only in that fixture.
- Add the same path to `refresh_base.KEEP_PATHS` so a newly recorded channel payload survives the reset (a pin raise must land its recorded fixture in the refresh PR).
- Extend `tests/test_refresh_base.py` with RED-first guards: acceptance + survival through the real `sync` over a real git repository, and a source-derivation guard that the recorder's own default path (read from the Makefile) is in both sets.
- Regenerate `OPENSPEC.md`; write the per-issue findings file.

## Impact

No stored value, contract, image or workflow wiring changes. The refusal path narrows by exactly one fixture a refresh legitimately writes; a genuinely foreign edit is still refused. No `AGENTS.md` rule change is expected — this extends an existing guard's path set, it does not add a stage.

## Not covered

- The two already-filed aggregate test failures (#1826 untraceable classification, #1827 `seen_posts` history) are separate issues and out of scope.
- No CI dispatch, no merge, no master push, no collaborator grant.
