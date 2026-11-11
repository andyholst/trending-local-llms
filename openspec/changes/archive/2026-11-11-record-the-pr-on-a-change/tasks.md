# Tasks

- [x] 1. Guard: `openspec_archive_check.py` reads an active change's `Issue:` ref (both header spellings via the shared `_refs`) and FAILS when it has no `PR:` line yet the issue is CLOSED, naming change + issue + archive remedy; a change naming a PR is judged by the PR whether or not its issue is closed; no-ref changes stay "nothing to assert".
- [x] 2. Guard: real-tree conformance — 110+ active changes whose issues are closed are MOVED to `openspec/changes/archive/` so the stricter guard is green after the change (additive only: moved, never deleted or rewritten). Verified via `python3 scripts/openspec_archive_check.py` with a real-devices stub on PATH (or the API) reporting each remaining active change's issue as OPEN.
- [x] 3. `scripts/openspec_record_pr.py` + `make openspec-record-pr ISSUE=<n> PR=<m>`: write `PR: #<m>` into every ACTIVE change whose proposal references `Issue: #<n>` (shared `_refs`), regenerate `OPENSPEC.md`; REFUSE (exit 2) when nothing matches.
- [x] 4. `issue-bot.yml` runs `make openspec-record-pr` right after opening the PR.
- [x] 5. `openspec_index._refs` parses BOTH `Issue: #N` and `**Issue:** [#N](url)` spellings (borderline form many changes use).
- [x] 6. qa-validate grants the validate job `issues: read` (the guard now reads issues as well as pull requests).
- [x] 7. Tests: `test_openspec_archive_check.py` extended (closed-issue prong, open-issue pass, PR-owned-by-PR, no-ref skip; stub gh answers issue state), new `test_openspec_record_pr.py` (writes line + index, refuses on no match, replaces existing PR line), `test_openspec_index.py` bolded-refs case; `make test` green.
- [x] 8. `ARCHITECTURE.md` (target + script rows, §8 wording), `AGENTS.md` §8 row, regenerated `OPENSPEC.md`, `findings.md`, `make lint` green.
