# Tasks

- [x] 1. The tracked change exists (this directory) before any edit.
- [x] 2. One sentence added to `docs/fleet-collaboration.md` section 4 item 4 stating the #690 small / single-purpose / non-breaking / one-issue-per-PR delivery rule, with split-or-flag before writing.
- [x] 3. One distinctive needle added to `COLLAB_NEEDLES` in `tests/test_fleet_lifecycle.py` (no new function, so `main()` is unchanged).
- [x] 4. RED/GREEN measured on the fetched base: base doc + new needle omits the sentence (RED); fixed doc + new needle passes `test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol` (FUNC_RC=0).
- [x] 5. `findings/1839.md` written with the analysis and the rulebook residual.
- [x] 6. `OPENSPEC.md` regenerated from `openspec/changes/**`.
