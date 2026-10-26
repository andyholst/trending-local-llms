# Tasks

- [x] 1. Write the proposal + `bot-alarm-configuration` capability spec for issue #489.
- [x] 2. `tests/test_workflows.py`: the scan, with `KEY="$KEY"` explicitly NOT an override.
- [x] 3. `.github/workflows/pr-health.yml`: the dead `MAX_FIXBOT_COMMITS:` entry removed, with the reason beside the command line.
- [x] 4. Verified RED against `origin/master`'s `pr-health.yml` (it names exactly the measured step and override) and GREEN after (884 passed).
- [x] 5. `findings.md` written.
- [x] 6. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
