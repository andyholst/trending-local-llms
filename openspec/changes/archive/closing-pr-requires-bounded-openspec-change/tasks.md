# Tasks: closing-pr-requires-bounded-openspec-change

- [x] 1. `scripts/openspec_archive_check.py` gains the change-required prong: each issue the PR closes must be named by an `Issue:` line of some change (active OR archived), parsed through `openspec_index._refs`; keeper/refresh head shapes exempt via `pr_closure.KEEPER_BRANCH`/`REFRESH_BRANCH` — VERIFIED: `tests/test_openspec_archive_check.py` 65/65 (4 new pins: refusal, archived green, keeper+refresh exempt, closes-nothing).
- [x] 2. The stub `gh` in the test answers `.headRefName` (`FAKE_HEAD_<n>`) — VERIFIED: same run, existing `--pr` pins unchanged.
- [x] 3. AGENTS.md §6f names the enforcement in the same change — VERIFIED: the sentence is in this branch's §6f.
- [x] 4. `ARCHITECTURE.md` §8 life-of-a-change names the fourth prong + `make architecture-refresh` regenerates the inventory block in the same commit — VERIFIED: `make architecture-check` green in this branch.
- [x] 5. `make openspec-index` lists this change; `make openspec-check` green — VERIFIED locally.
