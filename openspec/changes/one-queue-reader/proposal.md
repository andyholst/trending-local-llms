# The queue's pick has ONE reader, and it cannot truncate a value

**Issues:** [#547](https://github.com/andyholst/trending-local-llms/issues/547), [#548](https://github.com/andyholst/trending-local-llms/issues/548)
**Capability:** `issue-review-queue`

## Why

Two workflows read the same producer's output with two hand-rolled parsers, and only
one of them was ever driven by a test against the real output:

- `.github/workflows/issue-bot.yml` re-derived its pick from `make issue-queue`'s row
  with `sed -n 's/^issue=\([0-9][0-9]*\) position=0 .*/\1/p'` — a SECOND copy of a
  contract `scripts/issue_queue.py` already owns, expressed as a positional regex.
- `.github/workflows/issue-review-bot.yml` read each key with
  `sed -n "s/^${key}=//p" | head -1 | awk '{print $1}'` — taking the first
  whitespace-delimited token, so any value that ever gains a space is **silently cut**
  (`reason=window open` becomes `reason=window`). The same split is what once turned
  `ISSUE` into `266 position=-1 window=open …` (issue #344, run 39040689085), and the
  numeric guard that was added afterwards could not see it: it validated the truncated
  value.

The failure mode is the expensive kind. A truncated `issue=` spends a whole 20–30 minute
implementer run on the wrong number, and a truncated `reason=` erases the one fact a
human reads to answer "why did the sweep skip this issue?". Neither is visible in the
run's conclusion — both are green.

## What Changes

- **`scripts/issue_queue.py`** — the producer states its own contract:
  - `checked(key, value, allowed=…)` returns a value only when it is ONE token
    (`^[A-Za-z0-9_:.,/#+-]+$`) and, where the key is enumerated, one of its values;
    otherwise it **exits 2 naming the key and the raw value**. A bad shape is refused
    at the producer, never handed to a reader to guess at.
  - `--pick` prints exactly ONE line — `issue=<n>`, or `issue=` when the backlog is
    empty — and puts its reasoning (which issue was skipped and why) on **stderr**, so
    there is nothing left for a workflow to slice.
- **`scripts/issue_review.py`** — `_print_action` runs its four keys
  (`action`/`issue`/`path`/`reason`) through the same `checked()`, with `action` and
  `path` enumerated, so the reviewer's producer refuses a non-token value too.
- **`Makefile`** — one public `issue-pick` target wraps `--pick` (rule 6m: the
  workflow calls a target, never a script directly; rule 6d: the script is reachable
  from a target CI runs).
- **`.github/workflows/issue-bot.yml`** — the pick step COPIES the producer's value
  (`PICK="${OUT#issue=}"`) instead of re-parsing the row, keeps the numeric check as a
  loud failure, and writes the value with `printf` (never a whole-stdout redirect).
- **`.github/workflows/issue-review-bot.yml`** — the pick step takes each value
  WHOLE (no `awk`) and REFUSES a value carrying whitespace, naming the key and the raw
  value, instead of truncating it.
- **`tests/test_issue_review.py`** — the sweep's shipped step is now driven by the
  REAL producer's `--pick` stdout (a stub `make` is the external system), plus the
  producer-side refusals; the pre-fix shape now fails LOUDLY instead of being silently
  read as `266`.
- **`tests/test_workflows.py`** — the wiring guards follow the new contract (the sweep
  runs `make issue-pick` and contains no `sed` of the row; the reviewer's step contains
  no `awk` and does refuse whitespace).

## Impact

Only the bots' pick path. No data change, no README change, no ranking change. The
queued row format is unchanged, so `make issue-queue` still shows every candidate and
its reason; the new mode is additive.

## Not covered (out of scope)

- Unifying the two YAML `run:` blocks into one shared shell file: GitHub Actions has no
  cross-workflow shell include, and the repo's rule is "business logic lives behind a
  `make` target" — the remaining per-workflow code is a four-line key copy, and each is
  driven by a test against its producer (which is what #547 asked for).
- A `--parse` mode reading the producer's output from stdin: `DOCKER_RUN` mounts the
  checkout and has no `-i`, so a second container cannot read a piped row. The pick is
  therefore computed by the producer in ONE process.
- Issue #543 (the working-file reset list duplicated verbatim) and #541 (the PR title
  inline in the workflow): separate changes, tracked separately.
