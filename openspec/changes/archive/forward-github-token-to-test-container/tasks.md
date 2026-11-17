# Tasks — forward-github-token-to-test-container (#1095)

- [x] `TEST_RUN` forwards `-e GH_TOKEN` by name (Makefile)
- [x] qa-validate `Run unit tests (in container)` step maps `GH_TOKEN: ${{ github.token }}`
- [x] New wiring test drives `docker_test_run.sh` with a PATH-stubbed docker and pins the Makefile + step wiring
^- [x] Gates green: `make lint`, `make check-secret-output`, `make openspec-check`, full `make test`
^- [x] `make architecture-check` green (generated inventory still matches the tree)
^- [x] PR opened, closes #1095, change recorded+archived at the head
