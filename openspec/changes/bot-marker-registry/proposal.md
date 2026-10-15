# One marker registry: every bot marker defined once, read everywhere (issue #197)

**Issue:** [#197](https://github.com/andyholst/trending-local-llms/issues/197)
**Capability:** `bot-markers`

## Why

The three bots coordinate through timestamped markers in issue and PR bodies, and no shared state.
That makes a marker a **contract**: a writer (a workflow step, hours ago) and a reader (another bot)
must agree on a string neither of them owns. Nothing enforces it. A renamed or reworded marker
raises no error — the reader just finds no timestamp and concludes **"no implementer has started"**,
which is the exact collision the 3 h quiet window (#179) exists to prevent. The failure is silent
and it looks like a slow queue, not a bug.

Worse, the current reader already depends on an accident. `scripts/issue_queue.py` matched
`<!-- issue-review:` as a **substring**, and that string is a **prefix** of the window marker
(`<!-- issue-review: window …`). "Any reviewer activity" therefore worked only because one string
happens to start with another: a future rename of the window marker would silently drop reviewer
windows from the implementer's hold, and nothing would go red.

## What Changes

- **`scripts/bot_markers.py`** — the ONE definition of every bot marker: its name, its shape, its
  parser (`parse_markers` / `read_marker` / `ts_of`) and its writer (`start_marker` / `end_marker`).
  `REGISTRY` maps bot → kind → marker name; `ARTIFACTS` says which artifact each bot announces on;
  `WRITTEN` names the markers a writer in the tree emits today; `DECLARED_BY` names the markers
  whose writer lands with #198/#199 and the issue that lands it. The dedup keys
  (`data-gap-signature`, `tech-debt-signature`) are documented as search keys and never rewritten.
- **`scripts/issue_queue.py`** reads every marker through the registry. The `issue-review` union
  (start **or** window = reviewer activity) is now expressed explicitly instead of by substring
  accident.
- **`tests/test_bot_markers.py`** (into `make _test`) — round-trip for every registered marker, the
  two reviewer markers kept distinct, a placeholder stamp (`x`) refused as a marker, every
  `WRITTEN` marker proven to have a writer, and AGENTS.md rule 6j's table held in step with the
  registry.
- **AGENTS.md** — rule 6j carries the marker table (bot → artifact → markers) and §8 gets the
  guard row; **ARCHITECTURE.md** describes `scripts/bot_markers.py`.
- **`tests/test_issue_review.py`** — two fixtures used a placeholder `x` where a timestamp belongs,
  passing only because the old reader was a substring match; they now carry real timestamps.

## Impact

No behaviour changes for a well-formed marker: every string written today is unchanged, so no bot
run and no existing test depends on a new format. What changes is that a marker **without a valid
timestamp is no longer a marker**, and that the reviewer-marker union is explicit. That stricter
parse is what made the two fixtures' placeholders visible — a fixture that writes a marker no real
writer produces was testing the reader's leniency, not the product.

## Not covered

- The `fix-bot` start/end markers (#198) and the `refresh-bot` run marker (#199): their shapes are
  registered here so a reader is already correct, but the writers land in those issues.
- The `qa-validate` merge marker (`bot-merge`): registered, writer not yet landed.
