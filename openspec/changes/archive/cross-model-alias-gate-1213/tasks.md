# Tasks: cross-model-alias-gate-1213

- [x] Make `check_no_duplicate_measurements` honour `CROSS_MODEL_ALLOW_LIST` as the one justification seam (issue #1213 F1)
- [x] Fail closed on a stated-but-unparseable alias counterpart at ingest and REPORT it in the store gate (issue #1213 F2)
- [x] Add RED guards that fail on the fetched base for both findings and pass on the fixed head
- [x] Keep the shipped store green and #1210's flash-next <-> 27b hold untouched (no data or attribution edit)
- [x] Write `findings/1213.md` and regenerate `OPENSPEC.md` from the tree
