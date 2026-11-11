# issue-triage

## ADDED Requirements

### Requirement: The verdict grammar tolerates the formatting a model produces

`scripts/issue_verdict.py::parse()` MUST read the verdict from the decoration a model
actually writes around the grammar — leading markdown, a decorated or spaced colon, a
case-different key, emphasis or quotes around the value, and a trailing reason after the
verdict word — while keeping every existing refusal loud.

WHEN a TRIAGE-shaped line carries a verdict word among `implement`/`refine`/`close` as
its first value word, THEN that verdict is read, whatever markdown decorates the key and
value; a line whose first value word is not a verdict MUST exit 2 with no write, and a
file with no TRIAGE-shaped line MUST exit 2 with no write.

#### Scenario: a decorated implement verdict is read

- **Given** `triage.md` carrying `**TRIAGE: implement**`, `## TRIAGE: implement`, `- TRIAGE: implement`, `**TRIAGE:** implement`, `TRIAGE : implement`, `triage: implement`, `` `TRIAGE: implement` ``, an indented line, or `TRIAGE: implement — the thread matches the body`
- **When** the verdict is applied
- **Then** each exits 0 publishing `verdict=implement`, and no comment, label or close is issued
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at

#### Scenario: a decorated refine keeps its restatement

- **Given** a `triage.md` carrying `### **TRIAGE: refine**` and `**REFINED:** scope it to the ROCm table only`
- **When** the verdict is applied
- **Then** it exits 0, posts ONE comment carrying the restatement, and applies `agent:refined`
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at

#### Scenario: a decorated close keeps its evidence and reason

- **Given** a `triage.md` carrying `**TRIAGE: close**`, `**EVIDENCE:** scripts/issue_verdict.py:56` and `**REASON:** fixed on the base`
- **When** the verdict is applied
- **Then** it exits 0, posts the reason with its evidence, closes the issue and applies `agent:closed`
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at

#### Scenario: a near-miss that names no verdict is still refused

- **Given** `triage.md` carrying `TRIAGE: maybe`, `I implemented it.`, or prose that only mentions implementing
- **When** the verdict is applied
- **Then** each exits non-zero saying REFUSED and writes no comment, no close and no label
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at

### Requirement: An unknown verdict is never guessed at

A TRIAGE-shaped line whose first value word is not a real verdict MUST be refused
loudly, so decoration cannot turn "maybe" into a decision — and a line that lists the
whole grammar MUST NOT be read as the first verdict it names.

WHEN the only TRIAGE-shaped line names an unknown verdict, THEN the parser exits 2
naming it and the run writes nothing to the issue; WHEN every TRIAGE-shaped line lists
the whole grammar (`implement | refine | close`), THEN the parser exits 2 saying the
instruction was copied back rather than answered, and a real decision elsewhere in the
file still wins.

#### Scenario: an unknown verdict still refuses

- **Given** `triage.md` carrying `TRIAGE: maybe`
- **When** the verdict is applied
- **Then** it exits non-zero with `REFUSED` and `unknown TRIAGE 'maybe'`, and writes nothing
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at

#### Scenario: the copied grammar is not a decision

- **Given** `triage.md` carrying only `TRIAGE: implement | refine | close`
- **When** the verdict is applied
- **Then** it exits non-zero saying the instruction was copied back, and writes nothing
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at

#### Scenario: a pasted grammar line does not swallow the decision below it

- **Given** `triage.md` carrying the grammar line and, below it, `**TRIAGE: refine**` with a `REFINED:` restatement
- **When** the verdict is applied
- **Then** the refine is read and applied
- **Test:** tests/test_issue_triage.py::test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at
