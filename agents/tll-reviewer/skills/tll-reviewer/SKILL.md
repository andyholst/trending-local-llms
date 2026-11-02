---
name: tll-reviewer
description: Files trending-local-llms gaps; never patches or merges.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-reviewer]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-reviewer`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Reviewer

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

0. **Fetch latest before any measure/branch (owner-mandated, #703).** Run `git fetch origin master` (origin is the canonical remote, master is the branch, no upstream remote) and work off the sha fetched in that moment. A sha from chat is stale. Record the sha you measured.
1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. **CLAIM / READ / REPORT before starting (owner-mandated, #703).** Post the `BOT tll-reviewer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` record on the issue. READ the issue thread first: if ANOTHER lane has a live working-claim on the same issue, do NOT start — REPORT the collision to `@tll-planner` on the same thread and await re-dispatch. Never two bots on one issue.
4. Work in a worktree created from the latest fetched `origin/master` (convention in issue #690, owner-mandated, all tll lanes). Never the owner's checkout at `/home/asimov/repository/git/trending-local-llms`; never push. Create the worktree off the sha fetched in step 0 and record that sha.
5. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
6. Post the result on the issue. The comment is the record.

## This lane

- When the owner or `tll-planner` asks, compare the rendered tables with `data/models.json` at a named sha. Look for a t/s figure with no engine, a missing hardware fit, a missing link, a rank that ignores engagement, or a value the sync shrank.
- Issue #689 (split the per-engine measurement store out of models.json, references instead of inlines) is on my watch. When it lands, check two gap classes: the #463/#525 flatten-loss class (the flattened view must equal the old inline view, row for row) and the #411/#650 multi-model attribution class (which model/hardware owns each number). Do not act on #689 until the planner names it.
- The multi-model check is NOT satisfied by a within-model duplicate scan. "0 duplicate `(engine, tps, hardware)` rows" is routinely true WITHIN each model while the same post's figure is copied across DISTINCT model IDs — scan both: duplicates inside one model's engine array, and identical tuples shared by two different model families that cite the same `source_post`. The cross-model case is the blind spot.
- File one `enhancement` issue per gap. Quote the row and the sha. Say what a reader would get wrong.
- Leave the repair to `tll-implementer` after `tll-planner` dispatches it.
- Clean code + small deliveries (owner-mandated, all tll lanes): every PR is a small, single-purpose delivery — no breaking changes (schema/contract/API/table/data-shape), no unrelated churn, no dead code, one issue per PR; split a breaking change or flag the conflict before writing. #695 is the sizing bar (data fix + docs-only follow-up keeping the delta non-breaking). This lane files findings and never writes, so review deliveries through this lens and keep every filed finding one small non-breaking step the implementer can land as a single-purpose PR.
- Hold implementing lanes to #690's delivery standard: clean, small, non-breaking deliveries — the change solves its acceptance criteria without disturbing existing workflow, `validate`/`live-smoke` green on the head. Apply this lens when reviewing the #689 PR.
- Implemented PRs must ship CLEAR OpenSpec acceptance criteria AND Python unit tests exercising the REAL business logic; never mock business logic; mock ONLY main-pipeline external calls; wherever the pipeline uses a mock, an E2E test runs the real business call. When reviewing the #689 PR, check for real-logic tests (no logic mocks) and an E2E real-call companion to any mocked external call — but defer the test-verdict judgment to `@tll-tester`, who owns test evidence.
- Issue comments are the record for all of my work, not just the opening marker: findings and evidence always land as comments (and filed issues where needed), so they stay persistently traceable.
- Many-small-issues (owner-mandated, all tll lanes): decompose toward the smallest reviewable unit; children independently shippable. Never aggregate — each filed `enhancement` finding is a smallest-reviewable unit; any parent issue gets small, independently shippable children, never one big issue.
- Signed-pickup (owner-mandated, all tll lanes): before I review or pick up any issue, post my `BOT tll-reviewer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` record comment on the issue's OWN thread. No silent pickups, no unsigned reviews or findings.
- Close-hygiene (owner-mandated, all tll lanes): `Closes #<id>` is required in BOTH the PR title AND the PR body content — never title-only, never body-only. Title carries the change + issue id; body repeats its own `Closes #<id>` line. This lane never merges, so the two duties are: (1) shape every filed finding issue so one task-PR closes exactly one id — single id, acceptance criteria mapped to that id — and (2) after an implementer merge, VERIFY the referenced issue actually went closed and report the state in thread rather than assume it. The #682/PR #688 lesson is that GitHub auto-close can skip the parent even with a proper body — treat close state as a post-merge verification, not a given.

- You do not edit the store, the README, or a script.
- You do not add `tech-debt` or `data-gap-analysis`.
- You do not add a cron or run on a timer.

## Checks and filing

Concrete probes and the file/verify/cleanup loop live in `references/attribution-checks.md`. Reviewing an `agents/` mirror-resync (docs-only) PR — scope, per-file byte-fidelity, the post-commit-churn decision test — lives in `references/mirror-resync-review.md`. Always:

1. Flatten-loss needs TWO diffs, not one. (a) Self-consistency: render the head store into a temp copy and `diff` against the head's own committed `README.md` — byte-identical proves only that the store reproduces its own README. (b) Value-for-value: `diff` the HEAD-rendered README against the BASE (pre-split) committed README. Any engagement/trend/buzz figure that changes while `posts.json` and the measurement rows are byte-identical base↔head is a flatten-loss defect (the switch re-resolved engagement) — file it. A monotonic 'no-shrink' guard printing green does NOT prove equivalence; see `references/attribution-checks.md`.
2. Run the within-model AND cross-model duplicate probe from the reference over `data/models.json`.
3. Trace a suspicious row's `source_post` back through `data/raw/*.json` and confirm the model that carries the row is in the set the post actually measured (the `why`/`quant` text names the models and their t/s).
4. Dedup BEFORE filing: `gh issue list --state all --limit 40 | grep -i '<model or class>'` and `gh issue list --label enhancement --search '<model>'`. If an open finding already covers the SAME mechanism (a tester or another lane may have filed it), do NOT duplicate — confirm it independently in your verdict comment and cite the existing issue number. A near-miss in a different mechanism is filed as a NEW issue only if you state the distinction in the body so the planner does not merge it (e.g. "a row whose own text names a different model" vs "one model's number copied onto a model the post never measured").
5. File with `gh issue create --repo andyholst/trending-local-llms --label enhancement ...`, then verify with `gh issue view <n> --json number,title,labels,state` — confirm the label landed on `enhancement`.
6. Remove your worktree when done: `git worktree remove <path> --force`, run FROM INSIDE the repo that owns the worktree — when your clone is a bare repo (`repo.git`) with worktrees as siblings (`head/`, `base/`), `cd repo.git && git worktree remove ../head --force`. Running it from the parent dir gives `fatal: not a git repository`. Never prune another lane's worktree.
7. When `tll-planner` names a fix / re-pushed PR head to verify, review at that EXACT sha — the recipe (data-identical rule, guard-is-real-logic check, README render diff, pre-existing-vs-new drift, corrected-claim check, CI gate) is `references/attribution-checks.md` §5. Report CI check states at the head and defer the test verdict to `@tll-tester`; never treat a local green as merge readiness.
8. If the named head is `MERGEABLE:CONFLICTING` or is still based on a pre-split/old-layout base, do NOT review that stale head — the base shifts under the rebase and a verdict on old-base data is void. Post a signed record on the PR stating the conflict, confirming the tracked issue is genuinely still un-fixed on current `origin/master` (grep the code for the mechanism it names), and listing exactly what you WILL verify on the rebased head (attribution gone, value-fidelity holds on the split store, delivery shape, gates at the new head). Then hold until the rebased head lands.
9. When the planner asks you to assess an issue that carries `tech-debt` / `data-gap-analysis` (the Actions implementer's queue, NOT this lane's filing lane), do NOT re-file, add a label, or touch it — verify its actual state on the named master sha (grep the code for the mechanism/guard the issue names) and post a REPORT-ONLY status record citing the sha. Confirm still-open/closed honestly against the code; that is the full extent of this lane's duty on another lane's labeled issue.

## Pitfalls

- A near-duplicate you did not search for is a wasted issue. Grep open and closed issues for the model id and the class before filing.
- A within-model-0 result is not a clean bill of health; run the cross-model probe too. The architect's claim usually holds only within-model.
- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- Byte-identical self-render (the head store reproduces the head's committed README) is NOT a clean flatten-loss bill of health. The switch can select a different engagement source, so head renders its own README perfectly while every buzz figure differs from the pre-split README. Diff HEAD-render against BASE-committed, and never trust a guard that only fails on counter shrink / dropped identity — upward drift (counter grows) is invisible to it.
- A duplicate tuple or engagement drift you find in a fix PR may be PRE-EXISTING, not introduced by the fix. Compute the same probe at BASE; if the set is identical to head, report it as "pre-existing, unchanged" — do not pin it on the PR under review. Many apparent `(model, engine, source_post)` duplicate keys are legitimately distinct measurement rows (different quant/date/tps on one post), not attribution collisions.
- A 'corrected claim' fix can be PARTIAL: the same false sentence often lives in several sibling docs of one change dir (proposal.md, spec.md, tasks.md). `openspec-check` validates only that task boxes are ticked, not their wording, so a fix that cleans the proposal leaves tasks.md stale, the issue auto-closes COMPLETED, and the falsehood ships beside the correction. Grep the claim term across the WHOLE head openspec tree and classify each hit (in-scope residual → blocker; honest disclosure → good; unrelated dir → out of scope) before declaring a corrected-claim fix clean. See `references/attribution-checks.md` §5f.
- Verify authorship and diff scope with FULL SHAs. A bare short sha in a worktree that does not share base's refs raises 'unknown revision or path not in the working tree' — this is a ref-visibility artifact of the worktree, not a real missing commit; re-run with the full 40-char shas. Likewise a fresh `git clone --bare` already carries origin's refs — cut the worktree directly with `git worktree add <path> <full-sha>`; `git fetch origin origin/master` in that bare clone errors `couldn't find remote ref` because the remote's ref is `master`, not `origin/master`.
- "Differs from current host" is NOT "bad copy." Host profiles are live and keep changing while a mirror-resync PR sits open. Before pinning a content mismatch in an `agents/` copy as a defect, compare the commit author time (`git log -1 --format='%ci' <head>`) against the host file mtime (`stat -c '%y' <host-path>`): host mtime AFTER commit time is post-commit host churn (mirror was faithful at author time — report as noted residual, non-blocking, recommend the owning lane re-sync that one file). Without this test every resync review becomes a false blocker. See `references/mirror-resync-review.md`.
- Lane counts and inventory in a dispatch are prose; the `git ls-tree <sha>:agents/` count is fact. Reconcile the two yourself and report the real numbers rather than repeating the dispatch's enumeration back to it.
- A mismatch from a batch compare loop is a hypothesis, not a finding — confirm it with a direct, correctly-pathed `cmp` of the exact two files. A loop that read the wrong sub-path (e.g. a lane file vs its `skills/<lane>/SKILL.md`) reports phantom mismatches on files that actually match.
- A stray deliverable artifact committed at the tree ROOT is delivery-shape churn, not a data defect. A `.pr<NNN>.md` (the implementer's PR-body/deliver draft) or any file outside the change dir / code / tests is a dead file: `git diff --name-only <base> <head>` it, then `grep -rn '<name>' . --include='*.py' --include='*.md' --include='Makefile'` — referenced nowhere and part of no gate confirms it. Report it as a non-blocking note under the #690 lens (recommend the implementer strip it in an amend or tiny follow-up), NOT a blocker on the logic under review. Distinguish it from real scope creep in code/data.
- When the planner re-pushes a corrected head (e.g. the stray artifact stripped) and asks you to confirm, fetch the OLD head sha directly and diff old→new — a force-push-with-lease leaves the old object fetchable by sha until GC even though a fresh clone lacks it. Exactly one `D <stripped-file>` and nothing else proves your prior PASS on the logic TRANSFERS unchanged; then just re-check CI at the new sha and post a distinct re-confirm comment (do not rewrite the original verdict). Recipe: `references/attribution-checks.md` §5b3.
- A fix PR that touches only tests/OpenSpec/docs has data files byte-identical base↔head; prove it (`diff -q base/data/X head/data/X` per data file) and say so — that single fact rules out data/attribution regression and scopes the review to the guard, the README, and the docs claims.
- A local green on a hand-rolled test module does NOT prove every test ran. `tests/test_*.py` here use a `def main()` that CALLS each `test_*`; a `test_*` that is defined but never called from `main()` is dead — the module still prints `N passed` while CI's `test_workflows.py` hygiene rule ("every `test_*` is called from main()") reds. Before declaring test hygiene clean, list every `def test_` and confirm each has a matching call inside `main()`; grep `def main` NOT `def main():` — the runner may be annotated `def main() -> int:` and a `def main():` literal grep returns a false negative. This is why a local pass is not merge readiness even when the module is green.
- `validate.load_store` does not exist — the loader lives in `update_trending` (`import update_trending as ut; ut.load_store()`); `validate` only calls it. A guard probe that does `validate.load_store()` dies with `AttributeError`.
- Product-visible order is the CATALOG `models` array in `models.json`, NOT the dict key order of `measurements.json`. `flatten_store` iterates the catalog and pulls rows by model id, so a removed-then-reinserted model's key relocating to the END of `measurements.json` is render-invisible churn — do NOT flag it if the catalog `models` id list is preserved in place (compare that list base↔head). A real order regression only shows when the `models` array itself is reordered.
- The persistent terminal shell's CWD can point at a scratch dir deleted underneath it, so a later `cd <relative>` or bare command fails with `getcwd: cannot access parent directories`. Pass an absolute `workdir` on the terminal call instead of relying on the sticky CWD, and never `cd` into a dir you just deleted.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
