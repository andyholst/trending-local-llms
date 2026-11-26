# architect-wiki-role

## ADDED Requirements

### Requirement: All four architect role texts carry the wiki-freshness duty

The in-tree `agents/tll-architect/SOUL.md` and `agents/tll-architect/skills/tll-architect/SKILL.md`, together with the host copies `~/.hermes/profiles/tll-architect/SOUL.md` and `~/.hermes/profiles/tll-architect/skills/tll-architect/SKILL.md`, SHALL each carry the same `## Wiki / documentation freshness (issue #1773)` duty: measure each wiki/doc claim against the fetched tree; UPDATE a doc when its claim is false; ARCHIVE an obsolete doc into `docs/archive/` with a dated marker and a pointer; file one `enhancement` issue per change with measured evidence and the fetched sha; never invent a value; never hand-edit a generated artifact; amend the former 'no cron / no workflow' prohibitions ONLY for this duty; and have the weekly cron review the daily CI findings. No other lane's role text SHALL be modified by this change.

#### Scenario: the role mirrors lose the duty

- **Given** the freshly fetched base sha `37c6d88150fdb73fd0583a59099aee0b418d7927`, where all four role texts lack the duty heading and every behaviour needle
- **When** `tests/test_architect_wiki_role.py` reads the role texts
- **Then** the guard fails on that base (measured exit 1) and passes on the head (measured exit 0), so a future deletion of any needle is caught
- **Test:** `tests/test_architect_wiki_role.py::test_tree_role_mirrors_carry_the_duty`

#### Scenario: host and tree halves disagree

- **Given** a host profile home is mounted alongside the in-tree mirrors
- **When** the guard compares each host copy with its tree mirror
- **Then** a behaviour needle present in one half but absent from the other is refused, while a CI image without a host home skips that half explicitly
- **Test:** `tests/test_architect_wiki_role.py::test_host_copy_matches_its_tree_mirror_duty_text`

### Requirement: The guard proves RED against the pinned base and leaves generated artifacts to their generator

The guard SHALL pin the measured base sha rather than follow a moving `origin/master`, SHALL assert the duty is absent there, and SHALL NOT hand-edit `OPENSPEC.md`; the index SHALL be regenerated from the change set with `scripts/openspec_index.py --write` and verified with `--check`.

#### Scenario: the guard can no longer distinguish base from head

- **Given** a base blob that already carries the new duty heading
- **When** `test_red_on_the_pinned_base` inspects the pinned base role text
- **Then** it fails loudly instead of reporting a vacuous RED proof
- **Test:** `tests/test_architect_wiki_role.py::test_red_on_the_pinned_base`
