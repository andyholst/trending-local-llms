# Tasks: scratch-tree-outside-checkout-1505

- [x] Add the `_scratch(prefix)` / `_remove(path)` seams and point all three replay sites at them
- [x] Replace every `shutil.rmtree(tmp, ignore_errors=True)` with the loud `_remove`
- [x] Add the outside-the-checkout + residue guard and the loud-removal guard, registered in `main()`
- [x] Prove both guards RED against the pre-change behaviour (in-checkout path / `ignore_errors`) — `FAIL the scratch tree is built outside the checkout` and `FAIL a failing removal raises loudly`
- [x] Regenerate `OPENSPEC.md` (2 active, 496 archived) and run `make lint` (RC=0), `make architecture-check` (RC=0), `make findings-check` (13 findings, RC=0)
- [x] Focused module green (`refusal-grouping: 17 passed, 0 failed`); full `make test` green after the tick re-run
- [x] Write `findings.md` (the two sibling in-checkout scratch trees, filed separately — never fixed here)
- [x] Commit on `ci/tech-debt-scratch-tree-1505` and open the PR (`closes #1505`)
