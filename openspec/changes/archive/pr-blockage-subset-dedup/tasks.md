# Tasks: pr-blockage-subset-dedup

- [x] Drop a `group_pr_blockages` group whose member-run set is a strict subset of another emitted group's, keeping the superset that names every blocked branch
- [x] Add the RED-first guard in `tests/test_pipeline_failure_issue.py`: one defect on three open branches (two byte-identical whole blocks, one differing in chatter) emits 2 groups on the base revision and exactly 1 at the head, driven by the REAL `group_pr_blockages`
- [x] Prove the guard RED against `origin/master`'s `scripts/pipeline_failure_issue.py`
- [x] Keep the existing #1476 / #1175 / #1467 guards green
- [x] Run the focused module, `make lint` and `make openspec-check`; regenerate `OPENSPEC.md`
- [x] Write `findings.md`; commit on `fix/pr-blockage-subset-dedup-1565`, push, open a non-draft PR carrying `Closes #1565` in title and body
