# Proposal: secret-guard-file-set

Issue: #224 — `tech-debt: the no-secret-VALUE guard only scans a fixed suffix set`

## Why

`scripts/check_secret_output.py::tracked_files()` skipped every file whose suffix was not
in `.sh`/`.py`/`.yml`/`.yaml`/`.mk`/`.bash`/`.zsh` (plus `Makefile`) — while the module's
own docstring claims it scans “every text file a reviewer would call part of the repo”.
A value committed into a `.txt`, `.json`, `.toml`, `.md` or extension-less file was
invisible to every rule, and the file type nobody scans is the file type a one-line leak
survives in.

Widening the set naively is wrong, though, and this change measured it: with all text
files scanned, the guard immediately fired on the OpenSpec proposals that **quote** the
forbidden shapes (`openspec/changes/verdict-output-format/proposal.md` printing
`… | tee /dev/stderr >> "$GITHUB_OUTPUT"` in its own explanation) and on `AGENTS.md` §3d's
examples. Prose is not a leak.

## What Changes

- **The file set is every text file** under the root: a binary (NUL byte in the first
  8000) and an empty file are skipped — the same rule `scripts/lint_linefeeds.py` uses —
  and `SKIP_DIRS` still applies.
- **The rules are split by what they describe.** The **shape** rules (a committed
  credential literal) apply to every text file, because a real value pasted into prose
  is a leak. The **command-shaped** rules (a printed value, a value on `argv`, an env
  dump, a piped stdout, `set -x`) describe EXECUTION, so `executes_commands(path)` gates
  them to files whose lines are commands (`.sh`/`.bash`/`.zsh`/`.py`/`.mk`/`.yml`/`.yaml`
  and `Makefile`). A document that explains the rule is not committing the leak.
- **`tests/test_secret_output.py`** gains three cases: a credential literal in a `.txt`
  and a `.toml` is a violation (the widening), a document quoting `echo "$HF_TOKEN"` and
  `| tee /dev/stderr` is NOT, while the same document with a real value IS (the split),
  and a binary or empty file is never a finding.

Verified RED against the pre-change guard (3 failures — the `.txt`/`.toml`/document
values were invisible) and GREEN after (`PASSED 91 | FAILED 0`). Running the widened
guard over the real tree: 898 files scanned, no violations.

## Impact

`scripts/check_secret_output.py`, `tests/test_secret_output.py`, this OpenSpec change and
the regenerated `OPENSPEC.md`. The guard is the fail-closed backstop in qa-validate's
`validate` job; it now sees strictly more files and no fewer, and no target, stage, job or
image changes (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The key NAME set** (`SECRET_VARS`) — a second, related defect: it is a hand-maintained
  allowlist, so a new key added to a workflow is unguarded until someone edits it
  (issue #223). That is its own change.
- **A secret VALUE in a file that is not tracked at all** (a scratch artifact, an
  ignored log): the guard's subject is the repository, and `make scrub-log` plus the
  run-log audit (rule 3d) cover the log side.
