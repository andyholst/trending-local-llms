# Tasks — forward-github-token-to-test-container (#1095)

- [ ] `TEST_RUN` forwards `-e GH_TOKEN` by name (Makefile)
- [ ] qa-validate `Run unit tests (in container)` step maps `GH_TOKEN: ${{ github.token }}`
- [ ] New wiring test drives `docker_test_run.sh` with a PATH-stubbed docker and pins the Makefile + step wiring
- [ ] Gates green: `make lint`, `make check-secret-output`, `make openspec-check`, full `make test`
- [ ] `make architecture-check` green (generated inventory still matches the tree)
- [ ] PR opened, closes #1095, change recorded+archived at the head
