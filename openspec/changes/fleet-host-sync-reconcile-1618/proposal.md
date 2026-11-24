# Proposal: fleet-host-sync-reconcile-1618

Issue: #1618

## Why

After #1559, `make fleet-host-sync-check BASE=origin/master` reports six divergences on
asimov@mac: five lane `SKILL.md` mirrors and `tll-implementer/config.yaml`'s
`fallback_providers:` block. The config cause is measured and self-inflicted: the
owner-authorized #1591 fix set `security.protected_instruction_files: false` in the host profile but
not in the repo mirror, so a whole-copy re-provision would delete it. A hand-edit of a generated
config is refused by `make agent-model-chain-check`, so the setting needs a declared, renderable home
in the tree. The five skill divergences are the usual two-directional host/master drift: legitimate
host lessons have no delivery path, while host-only rewrites had dropped canonical master bullets.

## What Changes

- Add an OPTIONAL per-lane `agents/<lane>/config.append.yaml`: `render_lane` appends its bytes after
  `render_text`'s byte-exact chain output; an append may not redeclare `model:`/`model_aliases:`/
  `fallback_providers:`; a lane with no append file renders exactly as before.
- Declare the #1591 `security.protected_instruction_files: false` block in
  `agents/tll-implementer/config.append.yaml` and regenerate that lane's `config.yaml`.
- Provision lanes through `render_lane` (write and `--check`) so a whole-copy re-provision preserves
  the declared setting; non-lane merge homes keep the plain chain render.
- Land the legitimate host-ahead notes in five `agents/*/skills/*/SKILL.md` mirrors, with issue
  references intact, dropping host-state claims and keeping master's canonical bullets.
- Update the real test modules, `ARCHITECTURE.md` rows, `findings/1618.md` and this change's spec.

## Capabilities

- `fleet-host-config-mirrors` — declared lane config appends and two-directional skill mirror union.
