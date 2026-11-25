# Tasks: arm64-smoke-declares-qemu

- [x] Add one pinned `docker/setup-qemu-action@99012661954931238ded8c8b007157a8430204e1` step with `platforms: linux/arm64` before the arm64 QEMU smoke in the `build` job of `refresh-bot.yml`
- [x] Replace the false comment at the smoke with the runner-handler prerequisite
- [x] Add RED-first workflow-shape guards for the pinned step, its position, the single platform verdict and the smoke exec
- [x] Write `findings/1739.md` with the measured RED (`exec format error`, rc 255) and the native-arch control
- [x] Regenerate `OPENSPEC.md` and run the fast offline checks (`make lint`, action-pin check, targeted workflow tests)
