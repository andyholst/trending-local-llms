# Tasks

- [x] 1. Proposal + capability spec for `bot-agent-run-safety` (issue #386; measured on fix-bot run 39183131652)
- [x] 2. `scripts/scrub_log.py`: `--stream` redacts stdin line by line, prints each masked line at once, writes `--raw` and `--out`; the `--in` post-mortem mode is unchanged
- [x] 3. `Makefile`: `scrubbed_run` pipes the command through `--stream` under `bash -o pipefail`, so the command's exit status is the recipe's
- [x] 4. `Makefile`: `DOCKER_RUN` sets `-e PYTHONUNBUFFERED=1` explicitly, so the container's Python children flush per line
- [x] 5. `scripts/check_secret_output.py`: the `scrub-seam-is-not-live` rule refuses a seam that prints only after the command ends
- [x] 6. `tests/test_scrub_log.py`: the live stream, its refusal shapes, the unbuffered wrapper, and the seam driven end to end through `make`
- [x] 7. `tests/test_secret_output.py`: the pre-change seam is a violation and the shipped one is accepted
- [x] 8. `AGENTS.md` §8 row names the new guard
- [x] 9. `OPENSPEC.md` index refreshed (`make openspec-index`)
- [x] 10. Gates green in the workspace: `make lint`, `make validate`, `make validate-mapped`, `make test`, `make architecture-check`; the OpenSpec gate itself is executed on the PR by `qa-validate` (the CLI runs only in its container image, rule 6f)
- [x] 11. `findings.md` written for what this run touched
