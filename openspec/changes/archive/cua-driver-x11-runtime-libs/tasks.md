# Tasks: cua-driver-x11-runtime-libs

- [x] Add `libx11-6 libxi6 libxkbcommon0` to the single Dockerfile apt layer before the seam RUN
- [x] Add the additive Dockerfile-shape guard and wire it into `main()` (RED on the pinned base, GREEN on the head)
- [x] Prove the real staged arm64 `cua-driver 0.52.0` goes from "not found"/rc 127 to `cua-driver 0.52.0`/rc 0 with exactly those three packages
- [x] Leave the seam, the version-pin contract, the data, README, schema, tables and schedules untouched
- [x] Write `findings/1727.md` and regenerate `OPENSPEC.md`
- [x] Archive this change by NAME onto the branch head before the PR opens (issue #779)
