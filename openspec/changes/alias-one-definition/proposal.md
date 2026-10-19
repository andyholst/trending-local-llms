# Proposal: alias-one-definition

Issue: #221 — `tech-debt: The alias name has one definition for the config and many literals for the calls`

## Why

`HERMES_ALIAS := nous-deepseek` is the ONE definition the image uses: the `Dockerfile`
build writes `model.aliases.$(HERMES_ALIAS).*` from it and `make _hermes-alias-check`
reads every field back, failing the build on a mismatch. The **calls**, however, carried
the literal:

```
Makefile:428,433,438,443,491,898,1013,1030   -m nous-deepseek --reasoning …
```

Eight copies of one fact. A rename of the alias (or a second alias for a second model)
has to touch all eight, and nothing proves they agree with the definition the config is
built from — the exact drift the alias check exists to prevent, one level up. The tests
pinned the literal too (`re.match(r"\t\t-m nous-deepseek\b", …)` in two places), so the
suite would have defended the copies.

## What Changes

- **Every recipe uses `$(HERMES_ALIAS)`** for the model flag (8 sites). The one literal
  left is the definition itself (and a comment that explains what the Dockerfile writes).
- **The tests read the definition, never a literal.** `MODEL_FLAG` matches
  `\t\t-m $(HERMES_ALIAS) --reasoning`, `_defined_alias()` parses `HERMES_ALIAS` out of
  the Makefile, and the `make -n` dry-run assertions compare the EXPANDED flag against
  that value — so a redefined alias keeps the suite honest instead of pinning a name
  that is no longer used. Five assertions in `tests/test_hermes_prompts.py` and
  `tests/test_workflows.py` carried the same literal and now do the same.
- **`tests/test_hermes_prompts.py::test_the_alias_has_exactly_one_definition`** proves
  three things: the alias is defined once, every `\t\t-m …` recipe line uses the
  variable, and no recipe hardcodes the alias name; plus a `make -n` dry run per hermes
  target showing the flag expands to the defined value.
- The two existing vacuity checks (reasoning flags found, recipes really found) now
  count the variable form — so they cannot pass by matching nothing.

Verified RED against the pre-change `Makefile` (4 failures: the two vacuity counts drop
to 0 and both alias assertions list the eight literals) and GREEN after
(`PASSED 81 | FAILED 0`).

## Impact

`Makefile` (8 recipe lines), `tests/test_hermes_prompts.py`, this OpenSpec change and the
regenerated `OPENSPEC.md`. The alias VALUE is unchanged, so no pipeline behaviour
changes; no target, stage, job or image is added, renamed or removed
(`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The Dockerfile's `ARG`/`ENV` alias wiring** — it already reads `HERMES_ALIAS`, and
  `tests/test_install_hermes_ci.py` pins the pin-vs-Dockerfile agreement.
- **A second alias** (a second model for another stage): the point of this change is
  that adding one is now a one-line definition plus its call sites' variable, not eight
  edits; the choice of model stays a human decision.
