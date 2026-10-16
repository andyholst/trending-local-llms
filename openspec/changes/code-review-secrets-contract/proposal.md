# The code-review bot's secrets check runs without an admin credential

**Issue:** [#278](https://github.com/andyholst/trending-local-llms/issues/278) — `code-review-bot`'s secrets check is refused on every production run
**Capability:** `code-review-scan` (the bot's deterministic checks)

## Why

`make code-review-scan` reported **"no findings" on every production run while a third of its checks never ran**. Measured on `master`, run 38868116656 (2026-10-16T07:34Z), which finished **green**:

```
[code-review] WARNING: 'gh secret list --repo … --json name' was refused (1):
  HTTP 403: Resource not accessible by personal access token
[code-review] NOTE: the secrets check is unavailable here (it needs a token with admin on the
  repo); run the bot with one, or the check reports nothing.
[code-review] no findings: the checks found nothing to file
```

The cause is structural, not a bad credential: `defined_secrets()` asks GitHub's
`/actions/secrets` endpoint, which requires **admin** on the repository, and `code-review-bot`
deliberately runs on the default `github.token` with `contents: read` + `issues: write`. That
token can never read repo secrets, so the check was **skipped forever** — and a scan that says
"no findings" is indistinguishable from a scan that checked nothing. This is the same defect
class as the live checks that silently SKIPped (#209) and the search that reported "0 model
hits" for a refused fetch (#292/#293): a quiet pass for a check that did not run.

Worse, the check is the one that catches the failure it exists for. GitHub substitutes an
**empty string** for a `secrets.X` that does not exist, so a workflow naming the wrong secret
does not fail at startup — it fails later, wherever that value is used. Nothing was watching.

## What Changes

- **`scripts/code_review.py`** — the repo **declares its own secret contract**,
  `DECLARED_SECRETS`, and `check_secrets_not_defined` runs against it. The check is now
  **STATIC and unconditional**: `findings()` always runs it, so a credential can no longer
  disable it. A live `gh secret list` read, when a token with admin happens to be available,
  only **unions** in extra names — it narrows the check, never switches it off. `main()`'s
  misleading NOTE ("or the check reports nothing") becomes an INFO saying the contract was used.
- **`referenced_secrets()` / `_without_comments()`** — one implementation of "which secret names
  do the workflows read", with `#`-comments excluded. Measured: `qa-validate.yml:144` documents
  the guard with a literal `${{ secrets.X }}` in a comment, which raw scanning turns into a
  finding about the repo's own prose.
- **`tests/test_code_review.py`** — four new tests, in `main()`:
  - an undeclared secret **is** reported with no API read (RED on master: the check was skipped);
  - a declared secret, and `GITHUB_TOKEN`, are never reported;
  - **the contract equals what the workflows read, in BOTH directions** — a new reference forces
    a declaration and declaring a name nothing reads fails, so the contract cannot decay into the
    hand-maintained allowlist #223 complains about;
  - a commented reference is prose, not a read.

## Not covered

- **`AGENTS.md` §8's row** for these tests (rule 6c) could not be written: `AGENTS.md` is a
  protected rule file whose write is gated behind an approval prompt, which did not return. The
  row is owed and is deliberately NOT worked around — the same situation issue #212 records.
- **`ARCHITECTURE.md`** needs no change: no target, job, image or script is added or renamed.
- **`#231`** (a `workflow_dispatch`-only pipeline can ship broken because PR CI never executes
  it) is the sibling gap — this bot's checks are still not exercised on a PR — and is its own change.
