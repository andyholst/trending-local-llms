# Tasks: gateway-status-shape-1714

- [x] Add a RED-first guard in `tests/test_firecrawl_fetch.py` for incidental status digits, the real HTTP shapes, and the quiet/exit-1 end-to-end verdict
- [x] Prove the guard RED on the unmodified base revision of `scripts/update_trending.py`
- [x] Replace the bare gateway digit tokens with an HTTP status SHAPE matcher in `is_upstream_timeout`
- [x] Re-run the module GREEN, keeping the `#1699` and `#1707` guards intact
- [x] Regenerate the `ARCHITECTURE.md` §10 inventory after the docstring edit; run `make lint`, `make architecture-check`, `make check-secret-output`, `make openspec-check`
- [x] Write `findings/<issue>.md`, archive the change on the PR branch, open a non-draft PR and hand to `tll-reviewer`
