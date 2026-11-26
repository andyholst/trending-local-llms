# Tasks — refresh-bot-pin-token (issue #1747, token root cause only)

- [x] `.github/workflows/refresh-bot.yml`: aggregate job env gets `GH_TOKEN: ${{ github.token }}` with the measured rc=4 evidence in a comment
- [x] `tests/test_hermes_pin_freshness.py`: new guard locates the recorder's job and refuses a tokenless block or the owner PAT; wired into `main()`
- [x] RED-first probe: old workflow `FAIL`, new workflow `PASS` (job `aggregate:`, token from `github.token`)
- [x] OpenSpec change: proposal, `hermes-pin-freshness` spec with Test line, this checklist; index regenerated
- [x] `findings/1747.md` declares the owed AGENTS.md §8 row to the attended owner (rule 3c)
- [x] `make lint`, workflow-wiring checks; containerised `make validate` / `live-smoke` are CI-only — blocked: qa-validate runs on the pushed head
