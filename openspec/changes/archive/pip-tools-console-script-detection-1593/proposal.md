# Proposal: pip-tools-console-script-detection-1593

Issue: #1593
PR: #1566

## Why

The no-bare-host-python guard added for #1496 matched `python3|pip|uv` with a trailing `(?![\\w.-])` lookahead. The trailing `-` rejected `pip-compile`, `pip-sync` and `pip-tools`, so a planted bare `pip-compile …` in a NON-exception PUBLIC target exited 0 INVISIBLE even though the guard's own docstring promises to name any future bare host interpreter. `requirements.txt` is regenerated with exactly that command, so the one host invocation the guard most needed to see was the one it could not.

## What Changes

- Match the pip-tools console scripts as their OWN words, BEFORE the shorter `pip` alternative: `pip-compile|pip-sync|pip-tools|python3|pip|uv`. The near-miss exclusions (`python3.12`, `my-python3`, `scripts/pip`) stay excluded.
- Lock both polarities with the REAL detector and the REAL Makefile: a planted `pip-compile`/`pip-tools` in a non-exception public target is reported with target and line, while the real private `_requirements`/`_generate-requirements` recipes stay green because their only entry is a harnessed `$(DOCKER_RUN) make _x` hop.
- Reconcile the guard's docstring, its public target description, `ARCHITECTURE.md` and the OpenSpec index.

## Impact

One additive token-set widening to a guard that is still OPEN on PR #1566 and not yet on `master`. No new exception is granted, no existing detection is removed, and no schema, contract, API, table or data-shape changes. `make lint` stays green on the real tree.

## What is not covered

Issue #1596 (`$(MAKE)` hop blindness) is a different mechanism in the same guard and stays its own slice. The bare `piptools` module spelling is not added: the measured invisible spellings are the console scripts named above.
