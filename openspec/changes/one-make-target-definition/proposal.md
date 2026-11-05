# Proposal: one-make-target-definition

Issue: #512 — `tech-debt: "What is a make target" has two parsers`

## Why

Two scripts decide what a make target is, and they already disagree:

```
scripts/architecture_check.py  _TARGET_LINE ^([a-z][a-z0-9-]*):(?!=)   → public_targets
scripts/architecture_bot.py    make_targets: its own regex + the ## set
```

Measured on master: `len(architecture_check.public_targets(Makefile))` is 126 while
`len(architecture_bot.make_targets('.'))` is 178 — 52 internal `_`-prefixed targets the
public projection never sees, plus the `## description` set the generator unions in.
The check (a guard that must say "every public target is described") and the generator
(which renders "178 make targets") can drift apart without either turning red, and a
change to what counts as a target must be made twice — the exact second-copy-of-a-rule
drift rule 6d exists to prevent.

## What Changes

- **One scan, two views.** `scripts/architecture_bot.py` owns the single parser:
  `_scan_make_targets(text)` returns every `name:` target line (the full set), and
  `make_targets(root)` (unchanged public name, the full view) and the new
  `public_targets(root)` (the lowercase `[a-z][a-z0-9-]*` projection) are both
  DERIVED from it.
- **`architecture_check.py` imports the projection instead of defining its own.**
  It already imports `workflow_jobs` from `architecture_bot`; now it imports
  `public_targets` too and drops its private `_TARGET_LINE` / `_SKIP_PREFIX` and the
  local `public_targets` function.
- **One module, not a third.** The parser lives in `architecture_bot` (the generator
  that already counted targets); the check reads it, so a definition change is one
  edit, now two.
- **A consistency test** (`tests/test_architecture.py::test_public_targets_are_a_projection_of_the_full_set`)
  asserts on the real repository that public ⊆ full and the public set is EXACTLY the
  full set filtered to the public name shape — the two views cannot drift apart — and
  that `architecture_check` no longer carries a target-line parser of its own.
- **No count changes.** Both views render the same numbers as before (full 178 /
  public 126), so `ARCHITECTURE.md`'s generated §10 block is unchanged (rule 6h).

Verified RED: the new consistency test fails against the old tree (check defines its
own `_TARGET_LINE` and its public set was computed by a different regex).

## Impact

`scripts/architecture_bot.py`, `scripts/architecture_check.py`,
`tests/test_architecture.py`, this OpenSpec change and the regenerated `OPENSPEC.md`.
No target, stage, job or image is added, renamed or removed, so `ARCHITECTURE.md`'s
generated block is byte-stable (rule 6h).

## Not covered

- **The engine/`tests/test_architecture_bot.py` local `_makefile_targets()` helper** —
  it filters `workflow_targets` output with a loose regex; it is not the definition of
  "a make target", just a test-local filter. The new consistency guard covers the two
  real definitions this issue names.
- **`_ANY_TARGET` in `architecture_check.py`** — a deliberately looser match used only
  to name the target that carries a `--only` list in a failure message; it is not the
  count the guard or the generator render.
