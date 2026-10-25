# Tasks

- [x] 1. Write the proposal + `architecture-inventory` capability spec for issue #482.
- [x] 2. `scripts/architecture_bot.py`: `_ARCH_CALLS` + `script_arch_calls()`, `workflow_targets(text, targets, root)` appending a declaring script's targets, and `_arch_calls_problems(root)` refusing a non-target.
- [x] 3. The check runs at BOTH the `--write` path and the `--check` path, so a stale declaration cannot be published or pass.
- [x] 4. `scripts/fix_loop.sh` declares the eight targets it runs (`lint validate-search validate-mapped openspec-check architecture-check test fix findings-check`).
- [x] 5. `script_lines()` skips an `arch-calls:` line so the declaration is never rendered as the script's purpose.
- [x] 6. `tests/test_architecture_bot.py::test_targets_a_step_reaches_through_a_script_are_reported`: reported, refused, never rendered (75 passed).
- [x] 7. `ARCHITECTURE.md` regenerated — `fix-bot.yml` now names the targets its job really runs.
- [x] 8. `findings.md` written; `make openspec-check`, `make architecture-check`, `make lint` green.
