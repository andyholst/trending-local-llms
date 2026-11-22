# Proposal: pr-health-agent-login-1349

Issue: #1349

## Why

AGENTS.md rule 6s makes the open-PR rebase sweep MANDATORY — "a PR that is CONFLICTING or behind its base is RESOLVED — not noted" — and names `author.is_bot` as the ownership key. On this repository that key is always `false`: the agent login `asimov-agent` is a GitHub **User**, not a Bot (`gh api repos/andyholst/trending-local-llms/pulls/1289 --jq '.user.type'` answers `User`), so every agent PR answers `is_bot: false`. Measured on 2026-11-22: `pr_health.rebase_plan(<live gh payload>)` returned `{'human-branch': 22}` — zero `rebase-if-behind` — so the dispatched `make pr-health REBASE=1` rebased nothing and 15+ agent delivery PRs sat DIRTY with no repairer. Issue #1295 / PR #1296 rekeyed the sweep on `author.is_bot` precisely so agent `fix/…`, `feat/…` and `rule/…` branches would be swept; the fix is inert for the same reason.

## What Changes

- `scripts/agent_identity.py`: new `AGENT_LOGINS` — the ONE definition of the GitHub logins that carry the agent identity.
- `scripts/pr_health.py::is_bot_owned`: `author.is_bot` stays sufficient, but the author **login** is now checked against `AGENT_LOGINS` too. The branch-prefix list stays a fallback for callers that pass a head with no author data. `scripts/auto_merge_rebase.py` consumes the same seam, so the sweep and the pre-squash gate cannot disagree.
- `tests/test_pr_health.py`: the fixture carries the LIVE spelling (`is_bot: False` for `asimov-agent`), plus a RED-first guard for the login path and the unchanged mirror.
- `AGENTS.md` §6s states the author contract (login checked against `scripts/agent_identity.py`, `is_bot` sufficient not necessary) and §8 gains the row. Rule 3c: review-required.

## Impact

A behind-and-clean PR authored by the agent login becomes rebase-eligible; a CONFLICTING one is still never auto-rebased, and a human `ci/…` branch authored by `andyholst` stays report-only. No data format, contract, image or workflow wiring change.

## Not covered

- No change to the branch-prefix fallback, the conflict rule, or the push-identity (`GIT_PUSH_PAT`) contract.
- No CI dispatch, no merge, no `master` push, no collaborator grant.
