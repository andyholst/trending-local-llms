# Proposal: fix-openspec-archive-newline-1782

Issue: #1782
PR: #1783

## Why

`make openspec-archive NAME=<change>` runs the OpenSpec CLI, which writes the new `openspec/changes/archive/<change>/.openspec.yaml` without a final newline. That file is untracked at that moment, so rule 6i's `make lint-fix` (whose file set is `git ls-files`) cannot repair it, and the delivery's first `qa-validate/validate` reds at `Lint (every tracked text file ends with a newline)` on a file the pipeline itself just created (measured: PR #1774 head `000772fe`, run `45838927284`). Every archived file on the fetched base ends with a newline, so this is purely a defect at archive-creation time.

## What Changes

- Add `scripts/openspec_archive_newline.py`: after the CLI archive, append a final newline to every text file under `openspec/changes/archive/<NAME>/` that lacks one, including files still untracked (binary/NUL-bearing and already-correct files are untouched).
- Call that seam from the `openspec-archive` recipe immediately after `openspec archive $(NAME) -y`.
- Add `tests/test_openspec_archive_newline.py` driving the real seam against a planted archive dir and asserting the recipe wiring (RED on the pre-fix Makefile).
- Describe the new script/target in `ARCHITECTURE.md` and regenerate the derived inventory block.

## Impact

Additive and deterministic: the seam only appends a byte to files that lack it, never removes or rewrites a value (rule 3b). No data, contract, workflow or protected `AGENTS.md` rule text changes, so no rule-3c sign-off is owed for the seam itself. `make lint` on a fresh archived head becomes green without a manual `lint-fix`.

## Not covered

- No change to `openspec-record-pr` (it archives by moving an existing change dir, so it preserves already-correct bytes).
- No change to the OpenSpec CLI image or to `make lint` / `lint-fix` (their `git ls-files` scope stays as designed).
- No vendoring or patching of third-party archive output beyond the final-newline repair.
