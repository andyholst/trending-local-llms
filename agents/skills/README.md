# agents/skills — the ONE home of the leg contracts (issue #904)

Every agent leg in this repository runs from a project skill in this folder,
preloaded with `hermes -s <name>` (AGENTS.md §6p). The `Makefile` recipe is a
pointer plus that run's parameters; the rules themselves live here, ONCE.

`_setup` registers this directory in the container's Hermes home
(`make hermes-skills-register`), because a directory Hermes does not know makes
`-s` resolve NOTHING and the leg runs with no contract at all while reporting
success.

This folder replaced `.hermes/skills` (issue #904 reviewer ruling: the
`agents/` folder is the one home for agent skills; `.hermes/` was removed).

| skill | used by |
|---|---|
| `data-search` | the four `_search-<backend>` legs |
| `issue-implement` | `_implement-issue` |
| `issue-review` | `_review-issue`, `_review-issue-window` |
| `pr-fix` | `_fix` (the repair loop) |
| `bot-unattended` | every leg, beside its own skill |

Each `SKILL.md` carries `## Inputs`, `## Output`, `## Rules` and frontmatter
whose `name` matches its directory — `make check-agent-skills` (`make lint`)
enforces it, including that no skill re-spells a registered bot marker
(`scripts/bot_markers.py` is the ONE definition; rule 6j).
