# Proposal: one-person-one-identity

Issue: #445 (filed first, with the measurement)

## Why

**27 commits on `master` credit the same person twice in one message.** The squash author is the
owner's account (`Andy <andy.holst@protonmail.com>`) and the trailer is a *second spelling* of the
same human:

```
$ git log -1 --format='author=%an <%ae>%n%B' 5690eb8
author=Andy <andy.holst@protonmail.com>
ci: a silent PR is an alarm, not an empty check list (issue #442) (#443)

Co-authored-by: andyholst <andy@holst.se>
```

GitHub **synthesizes** that trailer from the author identity of a commit inside the PR: the PR's
commits were authored `andyholst <andy@holst.se>`, the merge actor is the owner's account, GitHub
sees two identities and credits both — and they are one person.

**Why the guard never caught it:** `scripts/check_commit_authorship.py` checks **WHO** may be
credited (`ALLOWED_NAMES` / `ALLOWED_EMAILS`), never **how many spellings** one person uses.
`andyholst <andy@holst.se>` is individually "allowed", so the rulebook's "the only identities here
are Andy Holst and Asimov Agent" was satisfied on paper while the log credited one human twice.

## What Changes

- **`scripts/agent_identity.py` gains `PEOPLE`** — each person with **one canonical
  `Name <email>`** (the identity the merge credits) plus the spellings that identify them
  (`person_of()`, `canonical_for()`).
- **`check_commit_authorship.py` refuses two new things**, each as its own named violation:
  - **a commit that credits its OWN author/committer a second time** — the measured `5690eb8`
    shape is a test fixture, verbatim;
  - **an author/committer written as a non-canonical spelling** of a known person, naming the
    canonical pair to use — because the spelling is what makes GitHub write the duplicate.
  A genuinely different person (`Asimov Agent` beside an Andy author) keeps passing: that is two
  people doing one thing, which is what a co-author trailer is *for*.
- **`AGENTS.md` §7 states the rule** (one person, one identity; the canonical pairs; why a second
  spelling is not a harmless alias) and **§8 gains the guard's row**, which was also owed (#322's
  §8 half).
- **Tests**: the measured commit refused; the second-spelling refusal naming the canonical pair;
  the real `master` history yields the self-credited commits (including `5690eb8`); a trailer
  naming a *different* person stays clean. The pre-existing "an allowed co-author trailer is not a
  violation" fixture is updated in the same change (rule 6b) — it credited the author's own person,
  which is now exactly what is refused.
- **`OPENSPEC.md` regenerated**, which also **repairs `master`'s red `validate`** (its index was
  stale: `96 active on disk` — the drift #304's remaining half describes).

Verified RED on the pre-change guard (the measured commit passes it) and GREEN after
(`PASSED 41 | FAILED 0` in the module; 40/0 inside the test container).

**One environmental fix came with it:** the runner's container mounts the WORKTREE only, and a
worktree's `.git` is a file pointing at the parent clone's `worktrees/<name>` directory — outside
those mounts. git answers `not a git repository`, the two tests that read real history got exit 2,
and the module failed in every worktree run (measured on a sibling worktree too, with `master`'s
scripts — pre-existing, not caused by this change). Both now probe readability first and report a
**named skip** instead of a false red; CI's own checkout is a normal clone, where they run strict.

## Impact

`scripts/agent_identity.py`, `scripts/check_commit_authorship.py`, `AGENTS.md` (§7 + §8),
`tests/test_commit_authorship.py`, `OPENSPEC.md`, this OpenSpec change. No new target, stage, job
or image — the guard already runs in `qa-validate`'s `validate` job.

## Not covered

- **Existing history is NOT rewritten.** The 27 commits stay as they are — rewriting `master` is
  forbidden (rule 1) and the guard's job is to gate new commits, which is how the `Hermes Agent`
  trailer was handled in #317.
- **The bot jobs' commit identity.** They already commit through the one seam (`make git-identity`)
  as the canonical agent identity (#439); this change makes the *interactive* commits hold the same
  line.
