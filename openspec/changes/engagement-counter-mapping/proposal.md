# Proposal: engagement-counter-mapping

Issue: #873

## Why

The `data-search` skill demands each captured measurement carry the post's likes,
comments, reshares and views "as integers", but never says **which rendered number on the
mirror is which counter**. The mirror renders the four counters unlabeled, so the leg maps
them by guess: the store holds 154/376 `engagement.seen_posts` with `views: 0`, 62 of them
beside `likes > 0`, and the checkable one — `lightbrd.com/dextune/status/2115088131636842866`
— is stored `likes: 10743, views: 0` while the page renders `17 / 35 / 378 / 20,2xx` in X's
fixed replies/retweets/likes/views order (re-verified live 2026-11-12). Ranking is
engagement-first (rule 4) and `score_7d` is composed of exactly these numbers, so a
neighbour card's figure silently moves a model's rank.

## What Changes

- The `data-search` skill names the mapping explicitly: a post page renders the four
  counters in X's fixed order **replies, retweets(reshares), likes, views**; search-result
  cards render the same order with zero counters omitted, so a card showing fewer than four
  numbers is ambiguous — the leg MUST open the cited post page whenever the card omits a
  counter it must store, and MUST NOT take a number from a neighbouring card.
- `check_post_signal`'s coverage line additionally prints **posts-with-views coverage**
  (`n/total with views`), so the 41%-views-zero regression class is visible in
  `make validate` and any future shrink of the mapping contract is measurable.
- Tests pin both: the skill's mapping wording (fails on the old skill text) and the views
  coverage report (fails on the old 3-tuple helper).

## Impact

- `.hermes/skills/data-search/SKILL.md` — the ONE post-counter contract the four legs preload (rule 6p).
- `scripts/validate.py` — `post_signal_coverage` gains a fourth metric; `check_post_signal` prints it (still report-only).
- `tests/test_post_signal.py` — new/extended assertions (rule 6c).
- No data or contract change; additive only (rule 3b). AGENTS.md §3 stays true unchanged — the mapping detail belongs to the skill, not the rulebook (rule 3c: this issue declares no AGENTS.md change).

## Not covered

- No backfill/correction of the already-stored mis-mapped counters (a data repair with its
  own human-visible diff; #873's Done-when is the contract + the visible coverage number).
- No failure gate on low views coverage — it stays a WARN like the rest of `check_post_signal`'s coverage line.
