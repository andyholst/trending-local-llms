# Tasks: rebaser-failures-announced-on-pr-thread

- [x] Register the `pr-health` marker family (`alarm`, `rebase_failed`) in
      `scripts/bot_markers.py` REGISTRY / ARTIFACTS / WRITTEN (rule 6j) — verified:
      `tests/test_bot_markers.py` 69/0, including the AGENTS.md §6j table agreement
- [x] `scripts/pr_health.py` stops spelling its markers privately: `MARKER` and
      `REBASE_MARKER` come from `bot_markers.marker_name` — verified: suite green
- [x] Announce failed rebaser rounds when `--rebase --comment`: `failed_rebases`
      (attempted-and-not-landed only), `rebase_run_key` (branch + head oid),
      `rebase_comment_body` naming `make worktree-resume` / `make base-rebase` —
      verified end to end: `tests/test_pr_health.py::test_a_failed_rebase_round_announces_on_the_pr_thread_once`
      (git-conflicting planted branch posts EXACTLY ONE comment; landed rebase posts
      nothing; failed branch byte-identical; 67/0)
- [x] Dedup through the SHARED parser: the next round reads its own marker off the
      thread via `bot_markers.parse_markers` and does not re-post — verified in the
      same test (round 2 posts nothing)
- [x] `AGENTS.md` §6j table row for `pr-health` (both markers) + §8 guard-row extension
      for the new test — verified: `tests/test_bot_markers.py` green against the table
- [x] Spec scenarios each carry a `Test:` line naming the real test — verified:
      `make openspec-check` (structure + reference gate) green on this branch
- [x] `make lint` green (linefeeds, workflow guards, secret scan) — verified on this
      branch (11 workflows scanned, guard scan OK)
- [x] `make test` full suite green on this branch — verified: every module rc 0
