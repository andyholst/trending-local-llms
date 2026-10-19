# Proposal: setup-output-visible

Issue: #222 — `tech-debt: \`make _setup >/dev/null\` hides the seam's own diagnosis on the wrapped targets`

## Why

Two wrapped targets ran the install seam with its output discarded:

```
Makefile:648  hermes-alias-check:  sh -c "make _setup >/dev/null && make _hermes-alias-check"
Makefile:699  hermes-smoke:        sh -c "make _setup >/dev/null && make _hermes-smoke"
```

`_setup` is the ONE installer seam (issue #207): it prints the path it took
(`already installed` → `HERMES_INSTALL_URL` → `uv tool install`, else FAIL), then
`hermes --version` and the `model.aliases.*` fields it writes. That output is the only
explanation a failed setup ever gives — and on these two targets it went to `/dev/null`,
so a run that died in the seam reported `make: *** [Makefile:648: hermes-alias-check] Error 2`
with nothing about why. Every other wrapped target (the four search legs, `fix`,
`implement-issue`, `review-issue`, `review-issue-window`) already kept it.

## What Changes

- **Both wrappers keep the seam's output, on stderr**: `make _setup 1>&2 && …`. The
  redirect goes to stderr rather than straight to stdout so the target's own output —
  the alias check's report, the smoke's verdict lines — stays what a caller parses,
  while a human reading the job log still sees the seam's reason.
- **`tests/test_install_hermes_ci.py::test_no_wrapper_discards_the_seams_diagnosis`**
  scans the real Makefile: the container wrappers are found (guard not vacuous), none
  discards `_setup`'s output, every one keeps it, and the two measured targets
  specifically are asserted by recipe.

Verified RED against the pre-change `Makefile` (4 failures, listing both `>/dev/null`
lines) and GREEN after (`PASSED 60 | FAILED 0`).

## Impact

`Makefile` (two recipe lines), `tests/test_install_hermes_ci.py`, this OpenSpec change
and the regenerated `OPENSPEC.md`. No target, stage, job or image is added, renamed or
removed, and the seam itself is untouched (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The wrapper's exit code.** A seam failure already propagates (`&&`); this change is
  only about the diagnosis reaching the log.
- **Capturing `_setup` into a file.** The job log is where a human looks; a scratch file
  would be one more artifact the bots must ignore, which is the class #390 just closed.
