# Tasks

- [x] 1. Proposal + capability spec for issue #852 (`message-pattern-enforcement`: the commit gate reads the CLAIM, not the first `#<n>`); rule-3c disclosure comment posted on the issue.
- [x] 2. `scripts/pr_closure.py::implemented_issue_from_message` — the ONE commit-side discriminator (claim = `implement(s) #<n>` verb on a reference, or a closing binding; a bare reference is not a claim).
- [x] 3. `scripts/pr_body.py::_commit_issue` delegates to it; the module header and docstring state the claim rule (no second copy of the pattern, rule 6d).
- [x] 4. `tests/test_pr_message.py::test_the_commit_gate_discriminates_an_archive_squash` — the exact `8965a45` message passes the real CLI; an `implement #635` title without the sections stays RED; a `Closes`-bound commit keeps its closure demand; plus `test_the_commit_claim_parser_lives_in_pr_closure` scanning the tree for the pattern.
- [x] 5. `AGENTS.md` §6e push-side sentence reworded to the CLAIM reading; §8 guard row added.
- [x] 6. Verified: `make test` (incl. test_pr_message / test_pr_closure / test_workflows / test_makefile_only), `make lint`, `make openspec-check`, `make architecture-check` green; the new test shown RED against the pre-change `scripts/` (fails on the old first-reference behaviour).
- [x] 7. `make openspec-index` regenerated; PR opened (ready, never draft) with the five-section body closing #852; CI watched to green; auto-merge armed by qa-validate; merge verified.
