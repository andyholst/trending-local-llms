# Proposal: commit-authorship-guard

Issue: #317

## Why

Nothing read a commit's **message** or a commit's **identity**. The three guards
this repo already had cover the other artifacts:

- `make secret-scan` (gitleaks) reads credential **values**;
- `make check-secret-output` reads run-time leak **shapes**;
- `make pr-closure` reads the **PR body**.

So a commit that credits anyone at all landed silently — and it already has.
Measured on `origin/master`:

```
$ git log --all --format='%B' | grep -i '^co-authored-by:' | sort | uniq -c
     32 Co-authored-by: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>
     22 Co-authored-by: andyholst <andyholst@users.noreply.github.com>
     10 Co-authored-by: Hermes Agent <agent@hermes.local>
      6 Co-authored-by: asimov <asimov@omarchy.local>
      2 Co-authored-by: asimov <asimov@example.com>
      2 Co-authored-by: asimov-agent <asimov-agent@users.noreply.github.com>
      1 Co-authored-by: Hermes Agent <hermes@nousresearch.com>
```

`Co-authored-by: Hermes Agent <hermes@nousresearch.com>` is already in the
history. The rule is that the only identities on this repo are **Andy Holst** and
**Asimov Agent** — nobody else.

### The measurement that shapes the design: the message alone is not enough

The one `hermes@nousresearch.com` trailer sits on master `4a4d78b`:

```
author=Andy <andy.holst@protonmail.com>
committer=GitHub <noreply@github.com>
parents=e1ee60c
---BODY---
fix(ci): a merged PR must close the issue it implements (#284) (#285)

Co-authored-by: Hermes Agent <hermes@nousresearch.com>
```

The subject carries BOTH `(#284)` and `(#285)` — the GitHub squash format
(`<PR title> (#<PR number>)`) — and the committer is `GitHub
<noreply@github.com>`. The trailer was **synthesized by GitHub at merge time**
from the AUTHOR IDENTITY of a commit inside the PR:

```
$ git log --all --format='%H|%an|%ae|%s' --author='hermes@nousresearch.com'
054b0c8|Hermes Agent|hermes@nousresearch.com|fix(ci): a merged PR must close the issue it implements (#284)
```

That commit's message has **no trailer at all** — only its author is wrong. A
guard that scanned messages only would have passed it, and the trailer would
still have landed on master. The same shape produced the ten
`agent@hermes.local` trailers (`7ad1c67`).

**Therefore the guard reads the identity AND the message.** This is the whole
point of the change, and it is locked by
`tests/test_commit_authorship.py::test_a_wrong_author_identity_with_a_clean_message_is_a_violation`.

## What Changes

- **`scripts/check_commit_authorship.py`** — the guard. Pure stdlib + `git log`,
  so host and container agree (like `make lint`). Two rules:
  1. every commit's **author and committer** identity in the range must be an
     allowed one;
  2. every crediting trailer in a commit **message** (`Co-authored-by`,
     `Signed-off-by`, `Reviewed-by`, `Tested-by`, `Acked-by`, `Helped-by`) must
     name an allowed one.

  Allowed: **Andy Holst** / `andyholst`, **Asimov Agent** / `asimov` /
  `asimov-agent`, plus the repo's OWN automation identities —
  `github-actions[bot]` (the `git config` in refresh-bot, fix-bot and
  issue-bot) and `GitHub <noreply@github.com>` (the committer GitHub uses for a
  squash). Refusing those two would redden every refresh/fix/issue-bot PR. Every
  other identity is refused and `Hermes Agent` is named in the failure.

  The default range is `origin/master..HEAD` — the commits a PR ADDS. History is
  never rewritten, so the pre-existing trailer in master's history does not red
  the guard. A range that cannot be read (a shallow clone, a missing ref)
  **FAILS LOUDLY (exit 2)**; it never degrades to "no commits, pass".
- **`tests/test_commit_authorship.py`** — one test per rule, driven against real
  throwaway git repositories (not mocks), plus the pass-on-this-repo self-test.
  No-skip policy: a missing prerequisite is a loud failure.
- **`make check-commit-authorship`** (the gate) and
  **`make commit-authorship-report`** (range, author, committer, subject) — both
  named in `ARCHITECTURE.md` (rule 6h).
- **Wired where it bites** (rule 6d): a step in `qa-validate`'s `validate` job,
  and `tests/test_commit_authorship.py` in `make test`. The `validate` checkout
  gains `fetch-depth: 0`, because the guard reads a range and a shallow checkout
  has no base ref.
- **AGENTS.md**: a new hard rule (an authorship rule in §2) and a §8 guard row —
  **OWED, not written**: `AGENTS.md` is a protected rule file and the write
  approval did not return, so the wording is recorded here, in the PR body and
  in its own issue rather than worked around (the #212 / #312 situation). Nothing
  in the tree cites a rule id that §2 does not declare, so
  `tests/test_rule_numbers.py` stays green.

## Impact

Compatibility: additive — a new guard, two new targets and one CI step; no
existing behaviour changes. The tree stays green; only a future regression goes
red, which is the point.

## Not covered

- **Rewriting the trailers already in history.** The guard gates NEW commits; it
  does not rewrite `4a4d78b` or `7ad1c67`, and it must not (`git rebase` over
  published master would rewrite every downstream SHA). Cleaning history is a
  separate, deliberate decision.
- **The source of the wrong identity inside a bot run.** The guard catches the
  commit; it does not stop whatever set `GIT_AUTHOR_*` to `Hermes Agent` in the
  first place. That environment seam is its own analysis.
