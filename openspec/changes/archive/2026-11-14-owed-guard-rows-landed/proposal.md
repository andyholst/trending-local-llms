# The §8 rows this session owed are written

**Issues:** [#543](https://github.com/andyholst/trending-local-llms/issues/543),
[#474](https://github.com/andyholst/trending-local-llms/issues/474),
[#362](https://github.com/andyholst/trending-local-llms/issues/362),
[#580](https://github.com/andyholst/trending-local-llms/issues/580)/[#583](https://github.com/andyholst/trending-local-llms/issues/583),
[#592](https://github.com/andyholst/trending-local-llms/issues/592),
[#522](https://github.com/andyholst/trending-local-llms/issues/522),
[#547](https://github.com/andyholst/trending-local-llms/issues/547)/[#548](https://github.com/andyholst/trending-local-llms/issues/548)/[#539](https://github.com/andyholst/trending-local-llms/issues/539)/[#578](https://github.com/andyholst/trending-local-llms/issues/578),
[#544](https://github.com/andyholst/trending-local-llms/issues/544),
[#563](https://github.com/andyholst/trending-local-llms/issues/563),
[#363](https://github.com/andyholst/trending-local-llms/issues/363)
**Capability:** `agents-guard-registry`

## Why

Rule 6c requires a guard's §8 row in the same change as the guard. Ten changes shipped their guards
and recorded the row as **OWED** in their own `findings.md`, because `AGENTS.md` is a protected file
and the write approval does not return in a headless bot run ("Silence is not consent", #310). The
guards are registered in `make test` and **undiscoverable from the rulebook** — the exact drift §8
exists to prevent.

Each row is one line; ten separate PRs would need ten approvals and ten review cycles for the same
protected file. This change applies them together, from the ledger each `findings.md` kept.

## What Changes

- **`AGENTS.md` §8** — ten rows, each naming the guard, what it catches, and the issue that measured
  the failure: the working-file list (#543), the reverse marker guard (#474), the terminal-tool pin
  (#362), the adopt that carries this run's work and leaves no marker (#580/#583), the adopt that
  refuses a branch that is not this run's work (#592), the re-read before the agent starts (#522),
  the silent captured recipe (#547/#548/#539/#578), the heredoc that is not a call (#544), the
  failed-merge reason (#563), and the search job that forwards `HF_TOKEN` (#363).
- **`AGENTS.md` §6j** — `issue-bot-already-fixed` joins the `issue-bot` row.
- **`scripts/bot_markers.py`** — that marker moves from `UNREGISTERED_OWED` into `REGISTRY`
  (`issue-bot`/`already_fixed`) and `WRITTEN`, so the reverse guard from #474 no longer needs an
  exception and the owed list is empty.
- **`tests/test_agents_rows.py`** — `test_the_rows_this_session_owed_are_written` pins all ten rows
  by issue and phrase, asserts the marker is registered, and asserts nothing is left owed.
- **`tests/test_bot_markers.py`** — the owed-list check now allows an EMPTY list (it may only
  shrink), which is what closing #474 looks like.

## Impact

The rulebook names every guard this session added. A reader of §8 can find them; a future change
that deletes one reds `make test` naming the row.

## Not covered (out of scope)

- The other owed rows from earlier sessions that this ledger does not cover (the #6b/§4/§6e wordings
  tracked by #375, #476, #494, #503, #512) are separate issues with their own text; they are not
  folded in here.
