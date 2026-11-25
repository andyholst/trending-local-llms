# Tasks: pin-raise-1723

- [x] Raise `HERMES_VERSION ?=` to `0.23.4` in `Makefile`
- [x] Raise `ARG HERMES_VERSION` to `0.23.4` in `Dockerfile`
- [x] Re-record the `v0.23.4` channel payload through `make hermes-pin-channel-record`
- [x] Run the pin guards and fast offline checks (`make lint`, targeted modules) in the worktree
- [x] Write `findings/1723.md` and regenerate `OPENSPEC.md`
- [x] Archive this change by NAME onto the branch head before the PR opens (issue #779)
