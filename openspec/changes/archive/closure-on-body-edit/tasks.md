# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `pr-closure.yml` triggers on pull_request incl. `edited`
- [x] 3. Its guard is the first job (rule 6j) and admits `pull_request`
- [x] 4. `closure` checks out and runs `make pr-closure` (rule 6m — no script is reached directly)
- [x] 5. The pipeline is read-only; qa-validate keeps its own gate
- [x] 6. `BOT_GUARDS` + `ARCHITECTURE.md` updated (rules 6j/6h)
- [x] 7. Verified RED without the workflow (FileNotFoundError) and GREEN after (721 checks)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-check` green; `make lint` and `make test` green
