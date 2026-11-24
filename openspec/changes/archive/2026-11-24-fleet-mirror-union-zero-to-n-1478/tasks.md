# Tasks: fleet-mirror-union-zero-to-n-1478

- [x] Extend `unexpected_growth()` so an absent-at-base unit (`base_count == 0`) with `head_n >= 2` is flagged — always for a whole `line`, and for a `clause` only when both copies sit inside ONE source line (real mirrors, real `git show`; no mocks)
- [x] Delete the genuine intra-line duplicate the strengthened predicate exposes at `agents/tll-reviewer/skills/tll-reviewer/SKILL.md` (exact duplicate, no rule content lost)
- [x] RED-first: prove the planted intra-line `0 -> 2` case fails on the pinned-base detector (module exit 1, exactly that check red) and passes here (exit 0)
- [x] Lock the false positive: two distinct bullets sharing a clause produce no `0 -> 2` growth
- [x] Verify the four real mirrors stay GREEN at head (`test_mirror_unions_add_no_duplicate_or_interleaved_bullets`)
- [x] Regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Run the focused module and `make lint` at the exact head
