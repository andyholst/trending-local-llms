# Tasks: strand-openspec-change-at-merge

- [x] 1. `scripts/openspec_archive_check.py`: drop the `PR:`-line exemption in
      `closing_pr_violations` — any ACTIVE change whose `Issue:` the PR closes
      fails, recorded or not (verified: the new fixture exits 1 with the new
      script; the OLD master script exits 0 on the same fixture — the guard
      fails on the code it replaces, rule 6c)
- [x] 2. `scripts/openspec_archive_check.py` `main()`: with `--pr`, read and
      report the closing set even when no active change remains, so a closing
      head whose change is already archived passes with the closing set named
      (verified: archived fixture exits 0, OK line `--pr 781 closes #768`)
- [x] 3. `tests/test_openspec_archive_check.py`: replace
      `test_the_closing_pr_prong_passes_when_the_change_names_that_pr` with
      `test_the_closing_pr_prong_fails_a_recorded_but_unarchived_change` and
      `test_the_closing_pr_prong_passes_when_the_change_is_archived_by_the_pr`
      (verified: 51 module checks pass on the host; the only two host-reds are
      the known `missing gh` fixtures — homebrew `gh` on the host PATH, absent
      in the CI image)
- [x] 4. `AGENTS.md` §6f restated (the exemption is gone; the merging head must
      already ARCHIVE its change) and the §8 guard row updated in the same
      branch (rule 3c review-required diff)
- [x] 5. Proposal + ADDED requirement with per-scenario `Test:` lines
- [x] 6. `make lint` and `make openspec-index-check` green on this branch;
      `make openspec-check`'s only red was THIS file's own unticked boxes
      (the self-referential gate) and it goes green with this tick (verified
      on the re-run)
- [x] 7. Full `make test` green on this branch — its only failing module was
      `test_check_openspec_tasks.py`'s real-tree scan for the same reason
      (verified on the re-run after this tick)
- [x] 8. PR opened with the five-section body and `closes #866` bound to issue
      #866 only (auto-merge then gates `validate` + `live-smoke` green on the
      head commit that already holds this change archived)
- [~] 9. This change archived on its own closing head by `make openspec-record-pr ISSUE=866 PR=<pr>` — blocked: the PR number exists only after `gh pr create`; the record runs on this branch immediately after opening (rule 6f's required shape)
