# Tasks: rulebook-pipelines-read-bullets-only

- [x] `rulebook_pipelines()` reads only bullet-line claims (`^- \*\*`<name>.yml`\*\*`), with its docstring naming issue #660 (verify: new test red on the old reader, green on the new one)
- [x] `tests/test_architecture.py::test_prose_naming_a_backticked_yml_is_not_a_claim` added: prose token not a claim, ghost bullet still a claim (verify: the new test and the existing ghost test both green)
- [x] Real repo green: `make architecture-check` on this head, `AGENTS.md` untouched (verify: gate exit 0)
- [x] `make test` suite green; OpenSpec gates (`openspec-check`, index current) green (verify: run output)
