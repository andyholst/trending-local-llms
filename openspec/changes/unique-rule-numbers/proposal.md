# Unique, resolvable hard-rule numbers (issue #270)

**Issue:** [#270](https://github.com/andyholst/trending-local-llms/issues/270)
**Capability:** `rulebook-integrity`

## Why

`AGENTS.md` §2 numbers its hard rules **by hand**, and nothing checks the numbering — so master
carried **two `6m.` rules**:

```
250:6m. **ONE path: business logic goes through the Makefile, ...
394:6m. **The searches must ask for the models we rank ...
```

It happened the same way twice: `#262` renumbered its rule `6l`→`6m` **because `6l` was already
taken** (the queued-alarm rule, #256); one merge later `#265` picked `6m` for a different rule.

The cost is concrete, not cosmetic — **two tests cited "rule 6m" and meant different rules**:

- `tests/test_makefile_only.py:3` — "(AGENTS.md rule 6m)" = the *ONE path* rule;
- `tests/test_query_coverage.py:196` — pinned the literal `6m. **The searches must ask…` = the
  *searches* rule.

So any citation of "rule 6m" in a PR body, an issue or a code comment is ambiguous, and the second
test would have gone red the moment anyone renumbered the *other* rule. The defect class is the one
this repo keeps meeting: **a hand-maintained index with no guard** (#197's hand-spelled markers,
#275's hand-listed bots).

## What Changes

- **The searches rule moves** `6m` -> `6o` (next free; `6n` is taken by the worktree rule), and
  `tests/test_query_coverage.py`'s assertion follows it. `6m` stays the ONE-path rule, so
  `tests/test_makefile_only.py` and the §8 row are untouched.
- **`tests/test_rule_numbers.py`** — the guard, wired into `make _test`:
  - no two rules in §2 share an id, and the parsed rule set is non-empty (a guard over nothing is
    a defect);
  - every `rule <id>` citation anywhere in the tree names an id §2 declares.
- **`AGENTS.md` §8** gains the row.

## Impact

Nothing changes about what any rule *says*; one rule's number changed and one assertion followed it.
The guard deliberately does **not** assert contiguity or order: §2 is ordered by topic, not by
number (on master `6m` sits before `6h`), and a missing `6a` makes no citation ambiguous —
uniqueness and resolvability are the invariants that bite.

## Not covered

- Giving rules stable IDs instead of numbers — a bigger design question; this makes the collision
  impossible to merge, not the numbering clever.
- `#199` (the refresh-bot window) — separate.
