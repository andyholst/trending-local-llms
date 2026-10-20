# Proposal: agent-identity-one-definition

Issue: #325 — `tech-debt: The agent identity is a literal repeated in every committing workflow`

## Why

The repository's agent identity existed as **five hand-kept copies of one fact**: the same two
`git config` lines in four places (`.github/workflows/fix-bot.yml`, `issue-bot.yml` twice,
`refresh-bot.yml`) plus `scripts/check_commit_authorship.py`'s own `ALLOWED_EMAILS`. Nothing
derived one from the other — issue #323 had to edit the same lines four times, the guard only
notices a disagreement *after* someone writes a fifth value, and a new committing workflow copies
whatever lines it finds. If the address ever changes, the whole fleet reddens at once and every
workflow must be edited again.

## What Changes

- **`scripts/agent_identity.py`** — the ONE definition: `AGENT_NAME`, `AGENT_EMAIL`, and the
  `ALLOWED_NAMES` / `ALLOWED_EMAILS` sets, with `--git-config` (set the identity) and `--json`.
- **`make git-identity`** (+ host recipe `_git-identity`) — the seam every committing job calls;
  `git config` is host-side, so it runs no image.
- **The four workflow sites now call `make git-identity`** — no workflow spells out the name or
  the address any more.
- **`scripts/check_commit_authorship.py` imports the allowed sets** from that module instead of
  keeping its own copy, so the guard and the identity cannot drift.
- **Guards**: the pre-existing committing-job guard now asserts the **seam** (and the absence of
  the literal); a new test asserts the guard's sets ARE the one definition, that no workflow
  carries the identity literally, and that the Makefile target runs the module. The two push
  harnesses (issue-bot's stub `make`, fix-bot's minimal temp clone) map the one target to the real
  definition rather than hand-writing the identity in a stub.

Verified RED against the pre-change tree (13 failures — no seam, no module, literals everywhere)
and GREEN after (`PASSED 728 | FAILED 0`).

## Impact

`scripts/agent_identity.py` (new), `scripts/check_commit_authorship.py` (imports instead of
duplicating), `Makefile` (two recipes), three workflows, `tests/test_workflows.py`, `ARCHITECTURE.md`
(target + script rows, rule 6h), this OpenSpec change and the regenerated `OPENSPEC.md`.

## Not covered

- **A GitHub Actions repository variable.** An external `vars.AGENT_EMAIL` would move the fact out
  of the tree, where no test can read it and a rename is invisible to a reviewer — the opposite of
  the issue's "one definition that the workflows consume *and the guard reads*".
- **The bots' commit MESSAGES.** Their authorship is checked elsewhere; this is about identity.
