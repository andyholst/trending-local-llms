## 1. The decision, as data

- [x] 1. `scripts/ensure_image.py decide [--force <bool>] [--dow <1-7>]` returns `built`/`test_built`/`publish_openspec`, the three tags, a `reason` per image and the four published-probes, with the rule unchanged
- [x] 2. `parse_bool` reads force strictly (`0/false/no/off/""` = OFF, `1/true/yes/on` = ON, anything else fails loudly)
- [x] 3. `make rebuild-decision` prints the decision and supplies the day (`date +%u` is the repo's one call site for it)

## 2. The workflow delegates

- [x] 4. `refresh-bot.yml`'s `build` and `openspec-image` jobs run `make rebuild-decision` and consume its outputs; no inline `docker manifest inspect` or `date +%u` remains
- [x] 5. Both decision steps set `set -o pipefail`, so a failed decision cannot pass as a green step with empty outputs (which would silently stop the toolchain rebuilding)

## 3. The record (rules 6b/6c/6d/6f/6h)

- [x] 6. `tests/test_ensure_image.py` drives every branch (current / missing tags / missing `:latest` / Sunday / forced, each asserting its reason) and the strict `FORCE` parsing
- [x] 7. `tests/test_workflows.py` asserts the delegation, the absence of inline probes/clock, `pipefail`, and that every consumed `steps.decide.outputs.*` is a key the script prints
- [x] 8. The five existing assertions that pinned the inline shell (`HASHED=0`, `[ "$FORCE" = "true" ]` ×2, `decide.outputs.tag`) moved to the new contract
- [x] 9. `ARCHITECTURE.md` (three job rows + the new target + the script row) and the README bullet (through its template) describe the decision as data
- [x] 10. `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`, `make lint` and `make secret-scan` are green on the branch
