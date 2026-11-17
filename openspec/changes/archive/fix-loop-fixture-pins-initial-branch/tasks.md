# Tasks: fix-loop fixtures pin their scratch branch (#1090)

- [x] 1. `tests/test_fix_loop.py`: the three bare origins init with
      `git init -q --bare -b master`; the three work repos and the no-progress
      repo init with `git init -q -b master`; the deliberate `main` fixture
      keeps its explicit `-b main`.
- [x] 2. `tests/test_fix_loop.py::test_the_scratch_fixtures_pin_their_initial_branch`:
      the module reads its own source and refuses any scratch `git init` call
      without an explicit `-b <branch>`; proven RED on the pre-fix file and
      green on the fixed one.
- [x] 3. Verified both host defaults: the module passes under the host default,
      under `init.defaultBranch=main`, and under `init.defaultBranch=master`
      (68 passed, 0 failed each), and the OLD fixture reproduces the issue's
      exact `git commit -qam` RC=1 failure under a main default.
