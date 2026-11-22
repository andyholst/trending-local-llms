## ADDED Requirements

### Requirement: Authenticated scratch subprocess

The scratch test harness SHALL pass an environment containing an authenticated GitHub
credential NAME to every subprocess it starts. When no token variable is present it SHALL
resolve one from the already-authenticated `gh` client at run time; it SHALL NOT embed or
print a credential value.

#### Scenario: Anonymous host quota exhausted

- **WHEN** the anonymous GitHub quota is spent
- **THEN** the engine reachability probe inside the scratch suite still authenticates
- **AND** the same tree gives the same result on consecutive runs
