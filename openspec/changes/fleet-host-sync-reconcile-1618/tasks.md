# Tasks: fleet-host-sync-reconcile-1618

- [x] Fetch `origin/master` and cut worktree `fix/fleet-host-sync-1618` from the measured sha
- [x] Add `config.append.yaml` / `render_lane` to `scripts/agent_model_chain.py` with the owned-block refusal
- [x] Declare the owner-authorized #1591 security block and regenerate `agents/tll-implementer/config.yaml`
- [x] Provision lanes through `render_lane` in write and `--check` modes
- [x] Reconcile the five host-ahead SKILL.md mirrors (keep issue references, drop host state, keep master's bullets)
- [x] Add RED/green real-logic tests for the append, the refusal and the re-provision path
- [x] Update ARCHITECTURE.md rows, findings/1618.md and regenerate OPENSPEC.md
- [x] Run focused test modules, `agent-model-chain-check`, `make lint`, `architecture-check` and the offline sync seam
