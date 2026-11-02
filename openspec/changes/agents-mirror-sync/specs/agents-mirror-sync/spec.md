# agents-mirror-sync

## ADDED Requirements

### Requirement: the agents/ tree byte-matches the host fleet profiles

Every lane's `SOUL.md` and `skills/<lane>/SKILL.md` under `agents/` must be a
byte-for-byte copy of the matching host profile, including lanes added this lift
(`tll-tester`, `tll-pr-rebase`) and the six existing lanes re-synced from their current
host content. The `agents/README.md` fleet table must list every lane profile, including
the two newly added rows.

#### Scenario: every lane file matches its host and the README lists all lanes

- **Given** the host Hermes fleet profiles for all supported lanes
- **When** the `agents/` tree is compared against those host profiles
- **Then** each lane's `SOUL.md` and `skills/<lane>/SKILL.md` byte-match the host, the
  two new lanes' directories exist, and `agents/README.md` lists every lane row
- **Test:** `cmp` each `agents/<lane>/SOUL.md` and `skills/<lane>/SKILL.md` against
  `/home/asimov/.hermes/profiles/<lane>/<same>`; grep `agents/README.md` for the
  `tll-tester` and `tll-pr-rebase` rows (host-env assertions; byte-copy verified by the
  author with `cmp`)
