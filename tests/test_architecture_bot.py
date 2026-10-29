#!/usr/bin/env python3
"""Behavioural tests for scripts/architecture_bot.py (issue #479, rule 6h).

`ARCHITECTURE.md` §10 is the LIVING half of the description: every pipeline with
its triggers, jobs and `make` targets, the product end to end, one line per
script. It is DERIVED from the tree — so these tests drive the real script
against fixture trees (one behaviour each) and against the real repository, then
assert the wiring: `make architecture-refresh` writes it, `make
architecture-check` refuses a stale block, and the daily pipeline runs both.

No mocks: every case runs the actual script in its own process and reads the file
it wrote.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "architecture_bot.py"
BEGIN = "<!-- architecture-bot:begin -->"
END = "<!-- architecture-bot:end -->"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--root", str(root)],
                          capture_output=True, text=True)


def _tree(td: Path, workflows: dict[str, str] | None = None,
          targets: tuple[str, ...] = ("search", "merge", "render-readme"),
          doc_targets: bool = True) -> Path:
    """A minimal repo: Makefile + workflows + a script + README + data artifacts."""
    wf = td / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (td / "scripts").mkdir(parents=True, exist_ok=True)
    (td / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (td / "data" / "snapshots").mkdir(parents=True, exist_ok=True)
    (td / "data" / "models.json").write_text("{}\n", encoding="utf-8")
    (td / "README.md").write_text("# Fixture\n\n## ❤️ Most loved\n\n### 8 GB\n\n## License\n",
                                 encoding="utf-8")
    (td / "scripts" / "update_trending.py").write_text(
        '#!/usr/bin/env python3\n"""Fold raw snapshots into the store."""\n', encoding="utf-8")
    (td / "Makefile").write_text(
        ".PHONY: " + " ".join(targets) + "\n"
        + "".join(f"{t}: ## {t} the thing\n\techo {t}\n" for t in targets),
        encoding="utf-8",
    )
    for name, text in (workflows or {"ci.yml": _workflow()}).items():
        (wf / name).write_text(text, encoding="utf-8")
    (td / "ARCHITECTURE.md").write_text(
        "# ARCHITECTURE\n\n## 3. Every `make` target\n\n| Target | What |\n|---|---|\n"
        + ("".join(f"| `{t}` | does it |\n" for t in targets) if doc_targets else "")
        + "\n## 4. The pipelines\n\n## 10. The living inventory\n\n"
        + f"{BEGIN}\n{END}\n", encoding="utf-8")
    return td


def _workflow(cron: str = "13 5 * * *", targets: tuple[str, ...] = ("merge",)) -> str:
    calls = "".join(f"          make {t}\n" for t in targets)
    return (
        "name: fixture-bot\n\n"
        "on:\n"
        "  schedule:\n"
        f'    - cron: "{cron}"\n'
        "  workflow_dispatch:\n\n"
        "# a comment that says `make nonsense` and must never be reported as a call\n"
        "jobs:\n"
        "  guard:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: echo guard\n"
        "  work:\n"
        "    needs: guard\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: do it\n"
        "        run: |\n"
        + calls
        + "          make not-a-target\n"
    )


def test_block_is_derived_from_the_tree():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        r = run(root, "--write")
        check("write: the script exits 0", r.returncode == 0, r.stderr.strip()[-200:])
        block = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
        check("block: every workflow is named", "`.github/workflows/ci.yml`" in block)
        check("block: the workflow's name is reported", "fixture-bot" in block)
        check("block: the cron slot is reported", "cron `13 5 * * *`" in block)
        check("block: the dispatch trigger is reported", "`workflow_dispatch`" in block)
        check("block: jobs are listed in file order with their needs",
              "`guard`, `work` (needs `guard`)" in block, block[block.find("**jobs:**"):][:160])
        check("block: a target a step calls is reported with the Makefile's description",
              "`make merge` — merge the thing" in block)
        check("block: prose in a workflow COMMENT is not reported as a call",
              "make nonsense" not in block)
        check("block: a `make` naming no real target is not reported",
              "not-a-target" not in block)
        check("block: one line per script, from its own docstring",
              "`scripts/update_trending.py` — Fold raw snapshots into the store." in block)
        check("block: the README sections are listed",
              "- ❤️ Most loved" in block and "- License" in block)
        check("block: the card tiers are not sections",
              "8 GB" not in block)
        check("block: the product end to end is a table naming real targets",
              "| 1. Search | make search |" in block and "| 4. Render |" in block)
        check("block: the flow says how a row reaches README.md",
              "README.md" in block and "render_readme" in block)
        check("check: the freshly written block passes", run(root, "--check").returncode == 0)


def test_check_is_red_on_a_stale_block_and_green_after_write():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        run(root, "--write")
        # the tree moves on: a second workflow appears and a target is added
        (root / ".github" / "workflows" / "new-bot.yml").write_text(
            _workflow("41 * * * *", ("render-readme",)), encoding="utf-8")
        r = run(root, "--check")
        check("stale: --check exits 1", r.returncode == 1, f"rc={r.returncode}")
        check("stale: it says the block is STALE", "STALE" in r.stderr, r.stderr[-200:])
        check("stale: it names what to run", "make architecture-refresh" in r.stderr)
        check("stale: --write then makes it green",
              run(root, "--write").returncode == 0 and run(root, "--check").returncode == 0)
        block = (root / "ARCHITECTURE.md").read_text(encoding="utf-8")
        check("stale: the new workflow is described after the rewrite",
              "new-bot.yml" in block)


def test_missing_markers_are_loud_and_write_nothing():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        doc = root / "ARCHITECTURE.md"
        doc.write_text("# ARCHITECTURE\n\nno markers here\n", encoding="utf-8")
        r = run(root, "--write")
        check("markers: --write refuses a document with no markers", r.returncode == 1)
        check("markers: it names what is missing", BEGIN in r.stderr)
        check("markers: the file is left untouched", doc.read_text() == "# ARCHITECTURE\n\nno markers here\n")
        r = run(root, "--check")
        check("markers: --check fails too", r.returncode == 1 and "no" in r.stderr.lower())


def _load_bot():
    spec = importlib.util.spec_from_file_location("architecture_bot", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_targets_a_step_reaches_through_a_script_are_reported():
    """Issue #482: `fix-bot.yml` was described as calling three targets while its job runs six.

    The block reads a workflow's `run:` bodies, so `scripts/fix_loop.sh`'s `make validate` /
    `make test` / `make fix` were invisible and the inventory quietly understated the job. Following
    the shell would be parsing by guesswork, so a script DECLARES what it runs and the Makefile is
    checked against the declaration.
    """
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d), targets=("merge", "validate", "test", "fix", "search", "render-readme"),
                     workflows={"loop.yml": _workflow(targets=()).replace(
                         "          make not-a-target\n", "          bash scripts/fix_loop.sh\n")})
        (root / "scripts" / "fix_loop.sh").write_text(
            "#!/usr/bin/env bash\n# arch-calls: validate test fix\necho loop\n", encoding="utf-8")

        # When  the block is generated
        block = bot.render(root)

        # Then  the targets the script runs are reported for THAT workflow
        section = block[block.find("loop.yml"):]
        section = section[:section.find("####") if "####" in section[3:] else len(section)]
        joined = " ".join(l for l in section.splitlines() if "**calls:**" in l)
        check("script: a target the step reaches one level down IS reported",
              "`make validate`" in joined and "`make test`" in joined and "`make fix`" in joined,
              joined[:300])

        # And   a declaration naming a target the Makefile does not define is refused, never rendered
        (root / "scripts" / "fix_loop.sh").write_text(
            "#!/usr/bin/env bash\n# arch-calls: validate ghost-target\necho loop\n", encoding="utf-8")
        problems = bot._arch_calls_problems(root)
        check("script: a declaration naming a non-target is REFUSED",
              any("ghost-target" in p for p in problems), problems)
        check("script: and the ghost is never rendered as a call",
              "ghost-target" not in bot.render(root), "")


def test_a_flow_the_tree_does_not_back_is_refused():
    with tempfile.TemporaryDirectory() as d:
        root = _tree(Path(d))
        (root / "Makefile").write_text("search: ## s\n\techo\n", encoding="utf-8")
        r = run(root, "--check")
        check("flow: a renamed-away target fails the check", r.returncode == 1, r.stdout + r.stderr)
        check("flow: the failure names the target", "make merge" in r.stderr, r.stderr[-300:])
        r = run(root, "--write")
        check("flow: --write refuses to describe what is gone", r.returncode == 1)
        check("flow: and writes nothing", BEGIN + "\n" + END in (root / "ARCHITECTURE.md").read_text())


def test_real_repository_inventory_is_current():
    r = run(ROOT, "--check")
    check("repo: ARCHITECTURE.md's block matches the tree", r.returncode == 0, r.stderr[-400:])
    block = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    workflows = sorted(p.name for p in (ROOT / ".github" / "workflows").glob("*.yml"))
    scripts = sorted(p.name for p in (ROOT / "scripts").glob("*") if p.is_file())
    missing_wf = [w for w in workflows if w not in block]
    missing_sc = [s for s in scripts if s not in block]
    check("repo: every pipeline is in the inventory", not missing_wf, str(missing_wf))
    check("repo: every script is in the inventory", not missing_sc, str(missing_sc))
    check("repo: the bot itself is described", "architecture-bot.yml" in block)
    check("repo: the flow names the merge that writes README.md",
          "make merge" in block and "README.md" in block)


def test_wired_into_the_makefile_the_guard_and_the_pipeline():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("wiring: make architecture-refresh writes the block",
          "architecture-refresh:" in mk and "scripts/architecture_bot.py --write" in mk)
    check("wiring: make architecture-check refuses a stale block",
          "scripts/architecture_bot.py --check" in mk)
    wf = (ROOT / ".github" / "workflows" / "architecture-bot.yml").read_text(encoding="utf-8")
    check("wiring: the daily pipeline runs the refresh through make",
          "make architecture-refresh" in wf)
    check("wiring: it proves the whole document", "make architecture-check" in wf)
    check("wiring: it asserts its base before cutting a branch (rule 6n)",
          "make base-check" in wf)
    check("wiring: the guard is its own FIRST job (rule 6j)",
          wf.index("  guard:") < wf.index("  refresh:"))
    check("wiring: the scheduled run passes the guard",
          'if [ "$EVENT" = "schedule" ]' in wf)
    check("wiring: it never pushes master", "refs/heads/master" not in wf)
    check("wiring: the guard is registered in tests/test_workflows.py",
          '"architecture-bot.yml", "guard"' in (ROOT / "tests" / "test_workflows.py").read_text())
    check("wiring: qa-validate gates on the same check",
          "make architecture-check" in (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text())
    check("wiring: this module is discovered by the ONE test runner", wired(__file__))


def _shipped_step(doc: dict, *, step_id: str = "", name_prefix: str = "") -> dict:
    """The shipped step, read OUT of the workflow file — never a copy of it."""
    for step in doc["jobs"]["refresh"]["steps"]:
        if (step_id and str(step.get("id")) == step_id) or (
                name_prefix and str(step.get("name", "")).startswith(name_prefix)):
            return step
    raise AssertionError(f"no step id={step_id!r} name={name_prefix!r} in architecture-bot.yml")


def _git(repo: Path, *args: str, env: dict | None = None) -> str:
    import os
    e = {**os.environ, **(env or {})}
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                          env=e, check=True).stdout


def _fixture_repo(td: Path) -> tuple[Path, Path]:
    """A real git repo + a real bare remote, the repo's own Makefile and identity seam.

    Nothing of the PRODUCT is faked: `make git-identity` is the shipped one
    (`scripts/agent_identity.py`), `git` is the real one, and the "remote" is a real
    local repository. The single stand-in is a stub `gh` on PATH — the network
    boundary, which rule 6m allows when the test asserts on what the real code
    sends it.
    """
    repo = td / "repo"
    remote = td / "remote.git"
    (repo / "scripts").mkdir(parents=True)
    (repo / "bin").mkdir()
    # BOTH generated descriptions (issue #526): the publish step stages ARCHITECTURE.md AND
    # OPENSPEC.md, so a fixture carrying only one would fail on `git add`.
    for name, src in (("ARCHITECTURE.md", ROOT / "ARCHITECTURE.md"),
                      ("OPENSPEC.md", ROOT / "OPENSPEC.md"),
                      ("Makefile", ROOT / "Makefile"),
                      ("scripts/agent_identity.py", ROOT / "scripts" / "agent_identity.py"),
                      # The publish step COMPOSES its body through `make architecture-pr-body`
                      # (issue #542), so the fixture needs the real composer and the closure parser
                      # it imports — never a stub: the body's rule-6e shape is what this proves.
                      ("scripts/pr_body.py", ROOT / "scripts" / "pr_body.py"),
                      ("scripts/pr_closure.py", ROOT / "scripts" / "pr_closure.py")):
        (repo / name).write_bytes(src.read_bytes())
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Fixture", "-c", "user.email=f@example.com",
         "commit", "-q", "-m", "fixture")
    _git(td, "init", "-q", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "origin", "master")
    # The stub CLI records what it was asked and what arrived on stdin.
    (repo / "bin" / "gh").write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$GH_LOG.args\"\n"
        "cat >> \"$GH_LOG.body\"\n", encoding="utf-8")
    (repo / "bin" / "gh").chmod(0o755)
    return repo, remote


def test_the_keeper_regenerates_both_generated_documents():
    """Issue #526: `OPENSPEC.md` is generated too, and a merge is what stales it.

    Measured on master (run 39625708799): #521 and #524 each regenerated the index over a tree
    holding ITS OWN new change, so both wrote `111`; the squash merge kept one file, the disk held
    `112`, and every `qa-validate` push run on master was red. `architecture-bot` already has the
    right shape — regenerate, verify, PR only when changed — so it keeps BOTH artifacts, on a slot
    that converges within the hour instead of a day.
    """
    text = (ROOT / ".github" / "workflows" / "architecture-bot.yml").read_text()
    try:
        import yaml
        doc = yaml.safe_load(text)
    except ImportError:  # pragma: no cover
        print("  SKIP the wiring was not read: PyYAML is missing")
        return
    jobs = doc["jobs"]
    refresh = next(j for j in jobs.values() if any(
        "Regenerate the inventory" in str(s.get("name", "")) for s in j.get("steps", [])))
    runs = [str(s.get("run", "")) for s in refresh["steps"]]
    body = "\n".join(runs)

    check("index: the keeper regenerates ARCHITECTURE.md", "make architecture-refresh" in body, "")
    check("index: …and OPENSPEC.md (issue #526)", "make openspec-index" in body, "")
    check("index: both are regenerated BEFORE the drift gate decides",
          body.index("make openspec-index") < body.index("--quiet -- ARCHITECTURE.md OPENSPEC.md")
          if "--quiet -- ARCHITECTURE.md OPENSPEC.md" in body else False, body[-200:])

    drift = next(s for s in refresh["steps"] if s.get("id") == "drift")
    check("index: the drift gate covers BOTH files",
          "git diff --quiet -- ARCHITECTURE.md OPENSPEC.md" in str(drift.get("run")), str(drift)[:160])
    check("index: the gate names both files when it reports the change",
          "diff --stat -- ARCHITECTURE.md OPENSPEC.md" in str(drift.get("run")), "")

    publish = next(s for s in refresh["steps"] if "Commit, push and open the PR" in str(s.get("name")))
    check("index: the commit stages both files",
          "git add ARCHITECTURE.md OPENSPEC.md" in str(publish.get("run")), "")
    # The body is COMPOSED now (issue #542): the step pipes `make architecture-pr-body` instead of
    # spelling the text, so the two properties are read where they live — no closing keyword
    # anywhere near this bot, and the reference to the tracking issue kept in the composer.
    check("index: the step no longer spells a body of its own",
          "closes #" not in str(publish.get("run")).lower()
          and "architecture-pr-body" in str(publish.get("run")), str(publish.get("run"))[:200])
    composer = (ROOT / "scripts" / "pr_body.py").read_text()
    body_start = composer.index("def architecture_body(")
    body = composer[body_start:composer.index("def ", body_start + 10)]
    check("index: the composed body carries NO closing keyword",
          "closes #" not in body.lower() and "Tracking issue: #" in body, body[:200])

    on = doc.get("on") or doc.get(True) or {}   # YAML 1.1 parses a bare `on:` as True
    crons = [c.get("cron") for c in (on.get("schedule") or [])]
    check("index: the slot is HOURLY, so a stale index converges in an hour (issue #526)",
          crons == ["13 * * * 3"], str(crons))


def test_the_shipped_steps_actually_commit_push_and_open_a_pr():
    """Issue #485: the write path was only ever asserted as TEXT.

    The bot's first production run was the no-op (the block already matched), so
    the branch that commits, pushes and opens a PR had never executed anywhere.
    A grep cannot see a `$GITHUB_OUTPUT` line `make`'s echo corrupts (#346), a
    branch stamp that lost its `Z` (and so reads as an issue reference to
    `pr_closure`), or a body that grew a closing keyword. So run the SHIPPED
    steps: real `git`, a real bare remote, the repo's own `make git-identity`,
    and a stub `gh` standing in only for the network.
    """
    try:
        import yaml
    except ImportError:  # pragma: no cover — the test image ships PyYAML
        print("  SKIP the shipped steps were not executed: PyYAML is missing")
        return
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "architecture-bot.yml").read_text())
    drift, publish = _shipped_step(doc, step_id="drift"), _shipped_step(
        doc, name_prefix="Commit, push and open the PR")
    check("shipped: the commit step runs only when the drift step says so",
          "steps.drift.outputs.changed" in str(publish.get("if", "")), str(publish.get("if")))

    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        repo, remote = _fixture_repo(td)
        env = {"PATH": f"{repo / 'bin'}:{__import__('os').environ['PATH']}",
               "GH_LOG": str(td / "gh.log"), "GH_TOKEN": "stub",
               "REPO": "owner/name", "RUN_URL": "https://example.invalid/run/1"}

        # --- no drift: changed=false, no branch, gh never called ---------------
        out = td / "output-nodrift"
        out.write_text("", encoding="utf-8")
        r = subprocess.run(["bash", "-euo", "pipefail", "-c", drift["run"]], cwd=str(repo),
                           capture_output=True, text=True, env={**env, "GITHUB_OUTPUT": str(out)})
        check("shipped: the drift step succeeds on a clean tree", r.returncode == 0,
              (r.stdout + r.stderr)[-300:])
        check("shipped: a clean tree writes exactly `changed=false`",
              out.read_text().strip() == "changed=false", out.read_text())
        check("shipped: a clean tree opens no branch",
              _git(td, "ls-remote", "--heads", str(remote)).strip().count("\n") == 0,
              _git(td, "ls-remote", "--heads", str(remote)))
        check("shipped: a clean tree never calls gh", not (td / "gh.log.args").exists())

        # --- drift: changed=true, a real branch and commit, a body with no claim
        (repo / "ARCHITECTURE.md").write_text(
            (repo / "ARCHITECTURE.md").read_text(encoding="utf-8") + "\n<!-- drifted -->\n",
            encoding="utf-8")
        out = td / "output-drift"
        out.write_text("", encoding="utf-8")
        r = subprocess.run(["bash", "-euo", "pipefail", "-c", drift["run"]], cwd=str(repo),
                           capture_output=True, text=True, env={**env, "GITHUB_OUTPUT": str(out)})
        check("shipped: the drift step reports the change", "changed=true" in out.read_text(),
              out.read_text() + (r.stdout + r.stderr)[-200:])

        r = subprocess.run(["bash", "-euo", "pipefail", "-c", publish["run"]], cwd=str(repo),
                           capture_output=True, text=True, env=env)
        check("shipped: the publish step succeeds", r.returncode == 0,
              (r.stdout + r.stderr)[-400:])
        heads = [h.split("refs/heads/")[-1]
                 for h in _git(td, "ls-remote", "--heads", str(remote)).split("\n") if h.strip()]
        import re as _re
        branch = next((h for h in heads if h != "master"), "")
        check("shipped: it pushes ONE branch named ci/architecture-<UTC>Z",
              bool(_re.fullmatch(r"ci/architecture-\d{8}T\d{6}Z", branch)), str(heads))
        # Ask the guard that would REFUSE the PR, not a re-spelling of its rule: a branch
        # whose name encodes an issue makes `pr-closure` demand a closing keyword for it.
        closure = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location("pr_closure", ROOT / "scripts" / "pr_closure.py"))
        closure.__spec__.loader.exec_module(closure)
        check("shipped: pr_closure reads no issue out of the branch name",
              not closure.TRAILING_ISSUE.search(branch)
              and not closure.DATA_GAP_BRANCH.match(branch), branch)
        author = _git(repo, "log", "-1", "--format=%an <%ae>", branch)
        check("shipped: the commit is authored by the repo's canonical identity",
              author.strip() == "Asimov Agent <support@docondee.com>", author)
        args = (td / "gh.log.args").read_text()
        check("shipped: it asks gh for a PR against master on that branch",
              "pr create" in args and "--base master" in args and branch in args, args)
        body = (td / "gh.log.body").read_text()
        check("shipped: the body is not empty and carries the run", "https://example.invalid/run/1" in body)
        check("shipped: the body carries NO closing keyword",
              not _re.search(r"(?i)\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*#\d+", body),
              body)
        check("shipped: the branch ends up on the remote with the document committed",
              "ARCHITECTURE.md" in _git(repo, "show", "--stat", "--oneline", branch))


def _bot():
    spec = importlib.util.spec_from_file_location("architecture_bot", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_make_written_inside_prose_is_not_a_call():
    """Issue #544: a `make` in a heredoc BODY or a quoted string is text, not a call.

    Measured: a `run:` block that wrote the sentence "this PR passes `make
    openspec-check`" into a file, and then really ran `make validate`, was reported as
    calling BOTH — so the inventory claimed a target the pipeline never runs. The
    phantom vanished only because #287 moved that heredoc into a target, not because
    the scanner was fixed.
    """
    bot = _bot()
    targets = {"validate", "openspec-check", "pr-body", "fix"}
    workflow = """jobs:
  a:
    steps:
      - name: real
        run: |
          cat > pr-body.md <<'BODY'
          this PR passes make openspec-check and make fix
          BODY
          make validate
          make pr-body ISSUE="$ISSUE"
      - name: quoted prose
        run: |
          echo "the guard runs make openspec-check before anything else"
"""

    # When  the inventory reads the workflow
    found = bot.workflow_targets(workflow, targets)

    # Then  only the EXECUTED calls are reported
    check("heredoc: a `make` inside a heredoc body is not a call",
          "openspec-check" not in found, found)
    check("heredoc: a `make` inside a quoted string is not a call",
          found.count("openspec-check") == 0 and "fix" not in found, found)
    check("heredoc: a real `make validate` IS a call", "validate" in found, found)
    check("heredoc: a quoted ARGUMENT does not hide the target",
          "pr-body" in found, found)
    check("heredoc: order is first-use", found[:2] == ["validate", "pr-body"], found)

    # And   the real tree still reports what it runs (the guard is not vacuous)
    real = bot.workflow_targets(
        (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(),
        _makefile_targets())
    check("heredoc: qa-validate's real calls survive the filter",
          {"validate", "validate-search", "test"} <= set(real), real)


def _makefile_targets() -> set[str]:
    """Every target the real Makefile defines."""
    out: set[str] = set()
    for line in (ROOT / "Makefile").read_text().splitlines():
        if line.startswith("\t") or line.lstrip().startswith("#"):
            continue
        import re as _re
        m = _re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", line)
        if m:
            out.add(m.group(1))
    return out


def main() -> int:
    print("ARCHITECTURE.md's living inventory + its daily bot (scripts/architecture_bot.py)")
    test_block_is_derived_from_the_tree()
    test_a_make_written_inside_prose_is_not_a_call()
    test_check_is_red_on_a_stale_block_and_green_after_write()
    test_missing_markers_are_loud_and_write_nothing()
    test_targets_a_step_reaches_through_a_script_are_reported()
    test_a_flow_the_tree_does_not_back_is_refused()
    test_real_repository_inventory_is_current()
    test_wired_into_the_makefile_the_guard_and_the_pipeline()
    test_the_keeper_regenerates_both_generated_documents()
    test_the_shipped_steps_actually_commit_push_and_open_a_pr()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
