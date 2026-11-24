# Proposal: rulebook-push-and-verify-1589

Issue: #1589
PR: #1598

## Why

Rule 3c requires design, reviewer sign-off, then implement. #1423 landed push-and-verify in the two lane
skill mirrors and explicitly deferred the `AGENTS.md` half (`Leave AGENTS.md §7b/§8 untouched (rule 3c
owns that half)`). #1482's reviewer flagged the same residual. Measured at base `0231f310`:
`push-and-verify` appears **0** times in `AGENTS.md`, `"CI verifies"` **0**, `CI-ONLY` **0** — the rule
has no rulebook home, so a rebuilt host or another machine loses it silently.

## What Changes

- `AGENTS.md` §7b gains ONE bullet: lanes change locally and PUSH; CI verifies — make the change in the
  worktree, run ONLY the fast offline checks (`python3 scripts/pr_body.py --check-body-file <f>
  --branch <b>`, `make lint`, the targeted unit module), push, confirm CI registered on the new head,
  report; the full `make validate`, the whole `make test` and `make live-smoke` are CI-ONLY.
- The §7b Rule 3c note gains ONE clause naming issue #1589.
- `AGENTS.md` §8 gains ONE row for `tests/test_push_and_verify_guard.py`.
- New `tests/test_push_and_verify_guard.py` pins the §7b bullet and the §8 row names-only.

No data, contract, workflow, Makefile, script or image change. No existing sentence is edited or deleted.

## Impact

Rulebook prose plus one guard module. `scripts/run_tests.sh` globs `test_*.py` and runs each module in its
own process, so the module is discovered with NO target change (rule 6d satisfied by the existing
`make test` bundle). RED on the base (`exit 1`, both tests fail), GREEN on the landing head (`exit 0`).

## Not covered

- #1482's §7b intro rewrite, its Rule 3c clause and its §8 store-file row (a separate landing).
- #1586's dispatch-guard §7b bullet and `tests/test_dispatch_guard.py` §8 row (a separate issue).
- Re-syncing the host profile homes from the merged tree.
