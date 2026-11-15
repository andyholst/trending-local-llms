# squash-identity-legacy-history

Issue: #835

## Why

GitHub rewrites the agent's identity at squash time: the merge actor is the owner
account, so every auto-merged commit on `master` carries the account display name
`Mr. Asimov <support@docondee.com>` — a second spelling `agent_identity.PEOPLE`
exists to refuse. Measured on the fetched tip 2026-11-15: **103** such commits
(101 committed by `GitHub <noreply@github.com>`, 2 pre-protection direct pushes).
Rule 3 forbids rewriting them, and the guard's bounded range
`origin/master..HEAD` keeps them out of its domain — but a stale `origin/master`
ref puts that same merged history INSIDE the range and
`make check-commit-authorship` exits 1 (measured locally, issue #835). The
exclusion that keeps the gate honest is implicit and undocumented: the next audit
or explicit `--range` reds on commits nobody may amend, and a reviewer cannot tell
a live violation from synthesized history.

## What Changes

- `scripts/check_commit_authorship.py` classifies git commits whose AUTHOR is the
  GitHub-synthesized account identity (`Mr. Asimov <support@docondee.com>`) AND
  whose COMMITTER is an automation identity (`GitHub <noreply@github.com>`,
  `github-actions[bot]`) or the same account shape: they are **legacy merged
  history** — reported as `legacy=N` in the gate output, never gated. The
  classification is bounded by shape (git itself supplies the list; it can only
  grow with commits that actually landed), not by a hand-kept SHA list that would
  need a new entry every merge.
- A NEW feature-branch commit spelling itself `Mr. Asimov` while committed as the
  agent (a misconfigured `git config`) is still refused — the exemption is for
  GitHub-completed shapes, not for sloppy local identity.
- The `--identity` seam stays strict: a job may never configure the account name.
- `AGENTS.md` §3f states the contract explicitly (rule 3c: this issue's option
  (b) names §3f as the section that changes): master squash commits carry the
  synthesized account identity, the gate's domain is new commits, its range stays
  bounded, and no gate may read master's merged history as new work.

## Impact

- `scripts/check_commit_authorship.py`, `scripts/agent_identity.py`
- `tests/test_commit_authorship.py` (three new tests)
- `AGENTS.md` §3f (review-required rule row)

## Not covered

- Rewriting the 103 merged commits (rule 3 forbids it).
- Branch protection itself (already guarded by #959 /
  `make check-branch-protection`).
