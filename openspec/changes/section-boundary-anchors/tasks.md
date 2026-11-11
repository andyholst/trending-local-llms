# Tasks

- [x] 1. The tracked change exists (this directory) before any edit
- [x] 2. Measured the gap: `section()` in `scripts/architecture_check.py` matched
  `## 6.` / `## 7.` by heading text, and `ARCHITECTURE.md`/`AGENTS.md` had no anchors
- [x] 3. `ARCHITECTURE.md`: `<!-- arch:targets -->`, `<!-- arch:pipelines -->`,
  `<!-- arch:scripts -->`, `<!-- arch:guards -->` beside their sections
- [x] 4. `AGENTS.md`: `<!-- agents:rulebook -->` beside §6b and `<!-- agents:style -->`
  beside §7
- [x] 5. `scripts/architecture_check.py`: the `_REQUIRED_ANCHORS` registry +
  `section(text, start, end)` + the `anchor_findings()` pass replace the
  heading-number slice; a missing anchor and an anchor with no heading are findings
- [x] 6. Proven the guard bites on the pre-change documents: `python3
  scripts/architecture_check.py` against `git show origin/master:AGENTS.md` reports
  both missing `agents:` anchors
- [x] 7. `tests/test_architecture.py`: one anchor constant shared by the fixture, and
  the five new cases (lost anchor, restored anchor, stranded anchor, renumbered
  sections, real documents carry every anchor)
- [x] 8. `AGENTS.md` §8: the `tests/test_architecture.py` row names the anchor guard
- [x] 9. `ARCHITECTURE.md` §6: the `architecture_check.py` row states the anchor
  boundaries
- [x] 10. `python3 scripts/architecture_check.py`, `python3 scripts/check_agent_skills.py`
  and the full suite (`bash scripts/run_tests.sh`) green on the real tree
- [x] 11. `OPENSPEC.md` regenerated (`python3 scripts/openspec_index.py --write`) and
  `python3 scripts/openspec_index.py --check` green
- [x] 12. Every tracked text file ends with a newline (`make lint` shape) and the diff
  holds no secret
