## ADDED Requirements

### Requirement: Agent access boundary

Agents in the fleet SHALL NOT grant collaborator access, repository invites, permission changes or team membership. An agent that needs access SHALL post the need on the shared issue thread and wait for the human owner; it SHALL NOT grant, request on another's behalf, or work around the boundary.

#### Scenario: A lane needs collaborator access

- **WHEN** a lane determines that a machine or agent needs repository access
- **THEN** it posts the need on the shared issue thread and takes no access action
- **AND** only the human owner grants or denies it

#### Scenario: Rule weakened

- **WHEN** the owner-only clause is removed from AGENTS.md rule 6v
- **THEN** `tests/test_access_boundary.py` fails with a named finding
