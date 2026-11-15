tasks.md — squash-identity-legacy-history (issue #835)

- [x] `scripts/agent_identity.py`: `SQUASH_NAME` + `synthesized_account_identity()` — the account display name on the agent email, named in ONE place (VERIFIED: guard imports it; suite green)
- [x] `scripts/check_commit_authorship.py`: `synthesized_legacy_commit()` shape classification (account author + automation/legacy committer) applied ONLY on the git-range path; offline `--identity`/`--message-file` seams stay strict; output reports `legacy=N` (VERIFIED: live stale-ref clone scenario — 78 legacy commits reported, rc 0, previously rc 1)
- [x] `tests/test_commit_authorship.py`: four tests wired into the suite — legacy squashes exit 0 with `legacy=N`; a feature commit claiming the account name is refused; `--identity` still refuses the name; AGENTS.md contract pinned (VERIFIED: PASSED 48 | FAILED 0)
- [x] `AGENTS.md` §3f: the synthesized-identity contract row (rule 3c review-required — this issue's option (b) names §3f) (VERIFIED: text-pinned test green; diff reviewed against master's §3f)
- [x] `make check-commit-authorship` green on the branch (VERIFIED: OK 0 commits, rc 0)
