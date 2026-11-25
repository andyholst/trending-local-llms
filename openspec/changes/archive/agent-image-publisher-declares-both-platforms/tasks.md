# Tasks: agent-image-publisher-declares-both-platforms

- [x] `scripts/ensure_image.py::publish` builds both refs with ONE `docker buildx build --platform <PLATFORMS> --push`; the plain build and the two separate `docker push` calls are gone.
- [x] `<PLATFORMS>` is derived at call time from `image_manifest_check.REQUIRED_PLATFORMS` (the existing import at `ensure_image.py:73`), with no second literal platform list and no host-architecture selector.
- [x] Tag recipe, no-op/force guard and `_serves()` registry verification in `publish()` are byte-unchanged; `decide`/`arch_flag`, the workflows, the Makefile, tags and `data/` are untouched.
- [x] `tests/test_ensure_image.py`'s fake-docker stub handles the additive `buildx build --push` shape (records `-t` refs and makes them readable), leaving the `build`/`push` cases unchanged.
- [x] `tests/test_publish_agent_image.py` moves the call-shape assertions to the Buildx form and adds the two slice-1 guards; all new `test_*` functions are called from `main()`.
- [x] RED-first proof on a pinned base worktree at `e1d9a5a7917628609c64393f4fcefa2a5e369a1f`: with the new tests overlaid, `publish` emits plain `build` + two `push`, `calls declaring a platform: []`, `PASSED 62 | FAILED 14`, exit 1.
- [x] GREEN on the head with the product change: `python3 tests/test_publish_agent_image.py` → `PASSED 76 | FAILED 0`, exit 0.
- [x] `findings/1724.md` records the measured defect and the done-when with signature, evidence and why.
- [x] `make lint` green; `scripts/openspec_index.py --write` regenerates `OPENSPEC.md`; the four scenarios carry resolvable `- **Test:**` lines.
- [x] PR body authored with all five required sections and `Closes #1724` in BOTH the title and the body, for a READY (never draft) PR.
