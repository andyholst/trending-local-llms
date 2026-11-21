# Proposal: findings-dedup-index-lag

Issue: #185 — "`make file-findings` can file a finding twice — the dedup list is eventually consistent"
PR: #1193

## Why

`scripts/file_findings.py::already_filed` read `gh issue list --label tech-debt` ONCE and
substring-matched the `<!-- tech-debt-signature: … -->` marker. GitHub's list index is
eventually consistent: an issue created seconds earlier is absent from that list. Measured on
this repo — `make file-findings ISSUE=178 PR=180` filed #181/#182/#183 and a second invocation
~10 s later filed #184, a duplicate of #182. The signature marker exists for idempotence, and
the dedup is not a nicety: the same class (a filing that returns success while its protective
label/index is not yet visible) is defect #161.

## What Changes

- `scripts/file_findings.py::already_filed` gains `attempts` / `delay`: a read that may follow
  a create re-reads the label list with a pause until the index catches up.
- `scripts/file_findings.py::file_findings` waits for a just-created issue to become
  discoverable before reporting success, and refuses (non-zero) when it never does — a run
  that exits green has left an issue the NEXT run can find.
- `tests/test_file_findings.py`: the gh stub becomes a small Python program that models the
  index lag (a created issue is invisible to `issue list` for `FAKE_GH_LAG` seconds), and two
  tests drive the real script — two immediate-succession invocations file exactly one issue,
  and a create that never becomes discoverable fails loudly.

## Impact

- A re-run of `make file-findings` (the fix-bot/issue-bot path, or a human) no longer files a
  duplicate of a finding filed moments earlier.
- Each filing costs one extra `issue list` read (the discoverability check). A run whose
  create never becomes discoverable fails loudly instead of reporting a false success.

## Not covered

- Cross-MACHINE dedup: the state is GitHub's index, so two machines filing the same signature
  inside the same lag window can still both create. That needs a shared record, not a retry.
- The data-gap analysis filer (`scripts/data_gap_analysis.py`), which has its own
  `already_filed` and its own `--search` read.
