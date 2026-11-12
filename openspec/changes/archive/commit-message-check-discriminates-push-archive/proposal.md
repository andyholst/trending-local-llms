# The commit gate reads what a squash commit IMPLEMENTS, not the first number it names

**Issue:** [#852](https://github.com/andyholst/trending-local-llms/issues/852)
PR: #853
**Capability:** `message-pattern-enforcement`

## Why

Rule 6f makes an archive commit **mandatory** for every merged change:
`chore(openspec): archive …`. Rule 6e/§771's push-side gate reads "the issue … from the
message's own `#<n>`" — implemented literally as *the first `#<n>` in the whole message*
(`pr_body._commit_issue` uses `re.search` over title + body). An archive commit names
PR numbers in prose (`#845/#846 … (#851)`) and makes no implementation claim, so the gate
invents an implemented issue for it: it demands the five sections an archive is not
required to carry, **and** refuses the closure ("the branch implements #845, but no closing
keyword binds to it"). The consequence is deterministic self-repetition: run 43216532672
reded push commit `8965a45` (the archive of the merged #848/#846), and its predecessor
run 43211580552 reded the same class — while the identical archive commit `f44c156` was
green, because its title happened to name no `#<n>` first. Every future archive — every
merged change ends in one — goes red, forever, and no job repairs a push to `master`.

## What Changes

- `scripts/pr_closure.py` gains `implemented_issue_from_message(message)` — the ONE
  commit-side discriminator: a message implements an issue only when it **claims** one —
  an `implements #<n>` verb directly on a reference, or a closing keyword binding — never
  because a number appears in it.
- `scripts/pr_body.py::_commit_issue` delegates to it (rule 6d: one implementation; the
  PR side keeps the branch-based `implemented_issue(branch)`, which is correct and
  unchanged).
- `tests/test_pr_message.py` locks both sides of the new rule against the REAL CLI: the
  exact `8965a45` archive message must pass, and a commit carrying an implementation
  claim (`implement #635`, or `Closes #635`) must still be held to the five sections and
  its own closes binding — the discrimination must not gut the gate.
- `AGENTS.md` §6e: the push-side sentence "the issue is read from the message's own
  `#<n>`" becomes "from the message's own implementation claim" (rule-3c disclosure was
  posted on issue #852).

**Not covered:** archives still carry no closing keyword (rule 6f/6e unchanged); the
historically-red push runs `43211580552` / `43216532672` stay red as evidence — history
is never rewritten (rule 3c/3b); PR-side discrimination is untouched.

## Impact

- Affected specs: `message-pattern-enforcement` (ADDED requirement)
- Affected code: `scripts/pr_closure.py`, `scripts/pr_body.py`, `tests/test_pr_message.py`,
  `AGENTS.md` (§6e wording + §8 guard row)
- Pipeline: unchanged wiring — `pr-closure.yml`'s `commit-message-check` push job already
  calls the target; only the parser's discrimination changes.
