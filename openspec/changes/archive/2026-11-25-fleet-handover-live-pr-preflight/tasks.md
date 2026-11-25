# Tasks: fleet-handover-live-pr-preflight

- [x] OpenSpec change created with `Issue: #1716`, proposal + capability spec + this checklist
- [x] `make pr-message-check PR=<n>` preflight added to all eight lane `SOUL.md` PR handover sections, with the non-zero refusal clause
- [x] Reviewer skill mirror carries the same preflight and refusal
- [x] `tests/test_fleet_lifecycle.py` gains the three guards, registered in `main()`; each proven RED against the pre-change tree and GREEN on the fixed one
- [x] Fast gates green after the last edit: `make lint`, `python3 tests/test_fleet_lifecycle.py`, `make openspec-check`
- [x] Change archived on the branch + `make openspec-index` regenerated; `make openspec-index-check` green
- [x] Findings written to `findings/1716.md`; PR opened ready with `Closes #1716` and the five-section body, CI registered on the head
