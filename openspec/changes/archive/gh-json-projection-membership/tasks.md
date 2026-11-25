# Tasks

- [x] In `scripts/gh_json_fields.py::check_argv()`, when the SAME argv carries `--json <fields>` AND `-q|--jq <expr>`, parse the listed fields through `parse_fields()` and require every path `jq_paths(expr)` reads to name one of them (top-level segment); refuse a path outside the list, naming the expression, path and listed fields
- [x] Keep the reviewer's boundaries: `jq_paths` returning None stays tolerated, no widening into arbitrary `--jq` algebra (`.[] | select(…)`, `//` fallbacks), and the four `repo view … -q .nameWithOwner` sites plus `keeper_pr.py`'s array projection stay green
- [x] RED-first guards in `tests/test_gh_json_fields.py`: planted `gh pr list --json number -q .title` FAILS on `git show origin/master:scripts/gh_json_fields.py` (assertion, not traceback) and PASSES here; pin the five shipped composite shapes green; wire `test_a_planted_json_projection_path_is_refused` into `main()`
- [x] Update `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row to name the enforcement
- [x] Write `findings/1676.md` (the hole + the owed `AGENTS.md` §8 row)
- [x] Run the fast offline checks (focused module, `python3 scripts/gh_json_fields.py --scan`, `make lint`) and regenerate `OPENSPEC.md`
- [~] Extend the `AGENTS.md` §8 row for `tests/test_gh_json_fields.py` so it names BOTH `--jq` halves (recorded `API_SHAPES` families and the `--json`-projection membership guard) — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
