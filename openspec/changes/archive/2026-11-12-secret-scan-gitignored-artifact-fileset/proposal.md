# The secret-scan gate scans the files git could commit — not every byte on disk

**Issue:** [#836](https://github.com/andyholst/trending-local-llms/issues/836)
**PR:** [#838](https://github.com/andyholst/trending-local-llms/pull/838)
**Capability:** `secret-scan`

## Why

`make secret-scan` is the pre-push gate (rule 3d), and it was going red on files
git can never commit. gitleaks `dir` mode walks **every checked-out file** and
never consults `.gitignore`: on 2026-11-12 a local `make test` compiled the
secret self-test's own planted FAKE credentials into
`tests/__pycache__/test_secret_scan_self_test.cpython-312.pyc`, and
`make secret-scan` failed with 6 findings — `generic-api-key`, `openai-api-key`,
`huggingface`, `aws-access-token` — all of them in bytecode. That bytecode
cannot be staged (`git add -A` skips it), was never intended to be scanned, and
blocked the working tree with a finding no commit could ever carry. The same
shape recurs for every future test that plants a credential fixture, so it is
not a fixture problem — it is a **fileset** problem.

The blunt fix — running gitleaks only over `git ls-files` — would also be wrong:
rule 3d scans the working tree **including staged and unstaged new files**, and
`git ls-files` sees only tracked ones.

## What Changes

- The scan keeps walking the full checked-out tree (the conservative half is
  kept), but writes its findings as a **JSON report**, and
  `scripts/secret_scan_report.py` becomes the ONE verdict (rule 6d): every
  finding is classified by **`git check-ignore`** — git's own semantics decide
  what git could commit, never a hand-kept path list that drifts.
- A finding in a **committable** file (tracked or untracked) fails the gate,
  exit 1, exactly as before. A finding on a **gitignored path** is reported as
  a build artifact and does not block — reported, never hidden. A scan that
  wrote no report is a loud exit 2: a scanner that silently writes nothing is
  the false green rule 3d exists to prevent, not a clean tree.
- `make secret-scan-self-test` gains the third direction: the planted fake
  compiled into a gitignored `__pycache__/` of a throwaway git repo must NOT
  red the gate, while the same fake in a tracked file MUST — the artifact
  exemption can never swallow a real finding.
- The JSON report itself is created and deleted inside the recipe and joined
  the ONE working-files list (rule 3d), so the scan leaves no artifact behind.

## Impact

- `Makefile`: `_secret-scan` recipe (report path + filter verdict).
- `scripts/secret_scan_report.py` (new — the decision),
  `scripts/secret_scan_self_test.py` (third direction),
  `scripts/issue_bot_working_files.txt` + `.gitignore` (the report file).
- `tests/test_secret_scan.py`: recipe-shape pins + an end-to-end fileset test
  against real git; `AGENTS.md` §3d + §8 row; `ARCHITECTURE.md` (rule 6h).
- No change to `secret-scan-history` (a committed value is committable by
  definition), to `.gitleaks.toml` (no allowlist is widened — the issue's own
  constraint), or to any CI job (qa-validate already runs both targets).

## Not covered

- Quarantine of the artifacts themselves: a `__pycache__` under the repo stays
  a host-hygiene matter (`make test` may clean it); the gate only stops treating
  it as a finding that can block a push.
- Any change to what counts as a credential shape: the ruleset and allowlists
  are untouched; a REAL value in a committable file still means "remove the
  value, rotate the key", never an allowlist.
