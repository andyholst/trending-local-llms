# Tasks — agent-work-host-only (#1055)

- [x] Rewrite `AGENTS.md` §6t(e): dispatch ban stated in full + the host path named by its targets (owner directive 2026-11-15; rule 3c sign-off is the directive itself)
- [x] Add `tests/test_workflows.py::test_agents_md_forbids_an_agent_dispatching_a_pipeline` pinning the clause at the wording, and call it from `main()`
- [x] Prove the guard fails on the OLD rulebook: the wording-only assertions are red against `git show origin/master:AGENTS.md` before the rewrite (verified locally against the pre-change text)
- [x] `make lint` and `python3 tests/test_workflows.py` green on the new head
- [~] Land the reviewed PR and archive this change at the merge head via `make openspec-record-pr` — blocked: the human's review/merge of PR #1056
