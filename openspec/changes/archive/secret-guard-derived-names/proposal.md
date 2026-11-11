# Proposal: secret-guard-derived-names

Issue: #223 — `the no-secret-VALUE guard's key set is a hand-maintained allowlist — a new key added to a workflow is invisible until added to SECRET_VARS`

## Why

Every rule in `scripts/check_secret_output.py` matched against a tuple a human maintained:

```python
SECRET_VARS = ("NOUS_API_KEY", "NOUS_PORTAL_API_TOKEN", "GH_TOKEN", "GITHUB_TOKEN",
               "FIXBOT_DISPATCH_TOKEN", "HF_TOKEN", "TYPESAFE_API_KEY", "FIRECRAWL_API_KEY")
```

A workflow that adds a NEW provider key — `OPENROUTER_API_KEY`, `OPENCODE_API_KEY`,
`ANTHROPIC_API_KEY` — is unguarded by every rule until someone remembers to edit that
tuple, while the module's docstring claims it guards the keys this repo uses. The guard
is the fail-closed backstop for a one-line leak, and its input set was a memory test.

## What Changes

- **`SECRET_FLOOR` is the floor**, not the set: the env names the run wrappers inject, the
  tokens GitHub provides, the bot's PAT and the plugin's provider key.
- **`secret_names(root)` derives the rest**: every name the workflows reference as a real
  `${{ secrets.<NAME> }}` expression. A reference IS the declaration — the credential is
  guarded the moment it is used, with no edit to the guard. A name mentioned in a
  **comment** declares nothing (`qa-validate.yml` quotes `${{ secrets.X }}` while
  explaining the rule; deriving `X` would guard a variable that does not exist — measured,
  and the reason the derivation reads expressions, not raw text).
- **`_patterns(names)`** builds the five value-shaped rules (value, expansion, argv,
  python read, name lookup) for the name set of the tree being scanned; `violations()`
  and `report()` use it, so the derived names apply to the file being checked rather than
  only to the repository at import time.
- **The four module-level regexes that made this impossible are gone** (`SECRET_VALUE`,
  `SECRET_EXPANSION`, `VALUE_IN_ARGV`, `PY_ENV_READ`) — they froze the name list at import
  and had no other caller.
- **Three tests**: a key a workflow references is guarded with no edit to the guard (the
  RED case); a floor name stays guarded with no reference at all; a name quoted in a
  workflow comment does not declare a credential.

Verified RED against the pre-change guard (a `secrets.BRAND_NEW_KEY` reference + an
`echo "$BRAND_NEW_KEY"` produced no violation) and GREEN after (`PASSED 88 | FAILED 0`).
The real tree derives exactly today's eight names and stays clean.

## Impact

`scripts/check_secret_output.py`, `tests/test_secret_output.py`, this OpenSpec change and
the regenerated `OPENSPEC.md`. The guarded set is now ≥ the old tuple for every tree, and
strictly larger whenever a workflow references a new key; no target, stage, job or image
changes (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The FILE set** — the sibling defect: the guard only scanned a suffix whitelist, so a
  value in a `.txt`/`.json`/`.md` was invisible. That is issue #224 and its own change in
  the same file.
- **A credential named nowhere and referenced nowhere** (a key only a human has): nothing
  in the repository declares it, so nothing can derive it; `make secret-scan` (gitleaks)
  covers a leaked VALUE rather than a printed NAME.
