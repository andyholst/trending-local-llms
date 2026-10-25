#!/usr/bin/env python3
"""Workflow wiring tests: refresh-bot -> qa-validate -> fix-bot.

Every one of these encodes a failure that actually happened in CI and that no
data test could see:

  - refresh PR authored by github-actions[bot] -> qa-validate held for a manual
    approval click (needs the owner PAT on checkout + `gh pr create`)
  - fix-bot dispatched at PR-open, before validation existed, without the
    failure report (must be dispatched by qa-validate, after `validate` fails)
  - fix-bot `workflow_run` trigger silently suppressed / double-firing
  - fix-bot looping under `bash -e`, never running `make validate`, committing
    with no git identity, pushing with GITHUB_TOKEN (CI never re-runs)
  - nothing live-tested the search / Hermes path on a PR

Parses the REAL .github/workflows/*.yml with PyYAML.

Run:  python3 tests/test_workflows.py   or   make test
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"

try:
    import yaml
except ImportError:  # pragma: no cover
    print("SKIP: PyYAML not installed (it is in requirements-test.txt)")
    raise SystemExit(0)

sys.path.insert(0, str(ROOT / "scripts"))
import agent_identity as _AI  # the identity's ONE definition (issue #325)
from update_trending import SEARCH_LEGS  # noqa: E402  ('nvidia', 'metal', 'cpu', 'amd')
import pr_closure  # noqa: E402  the pipeline's OWN closure parser (issue #289)

from wiring import wired  # noqa: E402  (issues #176/#192)

PAT = "secrets.FIXBOT_DISPATCH_TOKEN"
# The reviewer steps that consume the issue thread are gated on it (issue #344).
THREAD_GATE = "steps.iss.outputs.review == 'true' && steps.thread.outcome == 'success'"
_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def load(name: str) -> dict:
    d = yaml.safe_load((WF / name).read_text())
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True
    if True in d and "on" not in d:
        d["on"] = d.pop(True)
    return d


def steps(job: dict) -> list[dict]:
    return job.get("steps", [])


def step(job: dict, needle: str) -> dict:
    for s in steps(job):
        if needle.lower() in s.get("name", "").lower():
            return s
    return {}


def run_text(job: dict) -> str:
    return "\n".join(s.get("run", "") for s in steps(job))


def test_refresh_bot():
    wf = load("refresh-bot.yml")
    search = wf["jobs"]["search"]
    agg = wf["jobs"]["aggregate"]
    check("refresh: search matrix is exactly the search legs nvidia/metal/cpu/amd",
          search["strategy"]["matrix"]["backend"] == list(SEARCH_LEGS),
          search["strategy"]["matrix"])
    order = [s.get("run", "").strip() for s in steps(search) if s.get("run")]
    def idx(sub):
        return next((i for i, r in enumerate(order) if sub in r), -1)
    check("refresh: 3s reachability smoke runs before the search",
          0 <= idx("_search-smoke") < idx("make search-"), order)
    check("refresh: hermes routing smoke runs before the search",
          0 <= idx("make hermes-smoke") < idx("make search-"), order)
    check("refresh: model-caps check runs before the search",
          0 <= idx("make model-caps") < idx("make search-"), order)
    check("refresh: engine-check reports unregistered engines right AFTER each search (#73)",
          0 <= idx("make search-") < idx("make engine-check"), order)
    agg_order = [s.get("run", "").strip() for s in steps(agg) if s.get("run")]
    ec = next((i for i, r in enumerate(agg_order) if "make engine-check" in r), -1)
    mg = next((i for i, r in enumerate(agg_order) if "make merge-fetch" in r), -1)
    check("refresh: aggregate runs engine-check before the merge (#73)", 0 <= ec < mg, agg_order)
    checkout = step(agg, "checkout")
    check("refresh: aggregate checkout uses the owner PAT (push as owner)",
          PAT in str(checkout.get("with", {}).get("token", "")), checkout)
    pr = step(agg, "open PR")
    check("refresh: PR is created with the owner PAT (no approval gate)",
          PAT in str(pr.get("env", {}).get("GH_TOKEN", "")), pr.get("env"))
    check("refresh: does NOT dispatch fix-bot itself (qa-validate does, after validating)",
          "gh workflow run" not in run_text(agg), "")
    check("refresh: aggregate runs even if a search leg failed", "always()" in str(agg.get("if", "")), agg.get("if"))
    crons = [c.get("cron", "") for c in (wf["on"].get("schedule") or [])]
    check("refresh: two daily schedule slots (GitHub delays/drops scheduled runs)", len(crons) >= 2, crons)
    check("refresh: a backup slot off the top of the hour (minute != 0)",
          any(c.split()[0] not in ("0", "00", "*") for c in crons if c), crons)



def test_the_rebuild_decision_is_one_tested_unit():
    """Issue #208: `refresh-bot` reads the decision, it does not compute it.

    The rule ("Sunday, or a missing tag, or forced") used to be inline shell in
    TWO steps of this workflow, where no test could reach it — and the class has
    already cost this repo a silent stale toolchain (#135). It now comes from
    `make rebuild-decision` -> `scripts/ensure_image.py decide`, driven branch by
    branch in `tests/test_ensure_image.py`.
    """

    # Given the workflow and the script that owns the rule
    text = (WF / "refresh-bot.yml").read_text()
    script = (ROOT / "scripts" / "ensure_image.py").read_text()
    make = (ROOT / "Makefile").read_text()
    code_lines = [l for l in text.splitlines() if not l.lstrip().startswith("#")]

    # When  its decision steps are read
    wf_doc = load("refresh-bot.yml")
    all_steps = [s for j in wf_doc["jobs"].values() for s in j.get("steps", [])]
    decision_steps = [s for s in all_steps if "make rebuild-decision" in str(s.get("run", ""))]
    consumed = sorted(set(re.findall(r"steps\.decide\.outputs\.([a-z_]+)", text)))

    # Then  the decision is one target, with no probe left inline…
    check("refresh: both decision steps run `make rebuild-decision`",
          len(decision_steps) == 2, [s.get("name", "") for s in decision_steps])
    check("refresh: no inline `docker manifest inspect` remains",
          not any("docker manifest inspect" in l for l in code_lines),
          [l for l in code_lines if "docker manifest inspect" in l])
    check("refresh: no inline `date +%u` remains (the Makefile owns the clock)",
          not any("date +%u" in l for l in code_lines),
          [l for l in code_lines if "date +%u" in l])
    check("make: the target exists and calls the one script",
          re.search(r"^rebuild-decision:", make, re.M) is not None
          and "ensure_image.py decide" in make, "")
    make_code = [l for l in make.splitlines() if not l.lstrip().startswith("#")]
    # A failed decision must not be a GREEN step whose $GITHUB_OUTPUT is empty — every
    # build below is gated on those outputs, so the toolchain would silently stop
    # rebuilding. Two shapes satisfy that, and issue #346 retired the first:
    #   * `make … | tee … >> $GITHUB_OUTPUT` + `set -o pipefail` — the old shape; it also
    #     copied the whole stream (incl. make's echoed recipe) into the log and the
    #     output file, which is what killed the implementer's verdict step.
    #   * `OUT=$(make …)` + a bare assignment, then parsed `key=value` — the shape now.
    #     `bash -e` is the runner's default, so a non-zero command aborts the step.
    # The step must therefore CAPTURE and PARSE, and must not swallow the status.
    check("refresh: every decision step captures the output and writes parsed key=value",
          len(decision_steps) == 2
          and all("OUT=$(make rebuild-decision" in s.get("run", "")
                  and ">> \"$GITHUB_OUTPUT\"" in s.get("run", "")
                  and "| tee" not in s.get("run", "")
                  for s in decision_steps),
          [s.get("run", "")[:80] for s in decision_steps])

    check("make: the clock is read once, in the Makefile (never in a workflow)",
          sum("date +%u" in l for l in make_code) == 1,
          [l for l in make_code if "date +%u" in l])

    # …and every output the workflow CONSUMES is one the script PRINTS (this is the
    # cross-check that catches a renamed key: `tag` vs `openspec_tag`).
    printed = sorted(set(re.findall(r'^\s+"([a-z_]+)":', script, re.M)))
    missing = [o for o in consumed if o not in printed]
    check("refresh: every consumed decide output is printed by the script",
          missing == [], f"consumed={consumed} missing={missing}")

    # And the decision reaches the jobs that act on it.
    wf = load("refresh-bot.yml")
    check("refresh: the build job consumes built/test_built/base_tag/test_tag",
          {"built", "test_built", "base_tag", "test_tag"} <= set(consumed), consumed)
    check("refresh: the openspec job consumes publish_openspec and openspec_tag",
          {"publish_openspec", "openspec_tag"} <= set(consumed), consumed)
    check("refresh: the openspec build is gated on publish_openspec",
          "steps.decide.outputs.publish_openspec == 'no'" in text, "")
    check("refresh: the base build is gated on built",
          "steps.decide.outputs.built == 'yes'" in text, "")


def test_qa_validate():
    wf = load("qa-validate.yml")
    jobs = wf["jobs"]
    pr_paths = wf["on"]["pull_request"].get("paths", [])
    check("qa: workflow-only PRs are validated too (no !.github/** exclusion)",
          "!.github/**" not in pr_paths, pr_paths)
    v = run_text(jobs["validate"])
    for t in ("make validate", "make validate-search", "make validate-mapped", "make test"):
        check(f"qa: validate job runs `{t}`", t in v, "")
    check("qa: validate job has no network-dependent targets",
          "validate-fetch" not in v and "smoke" not in v, v)
    live = run_text(jobs.get("live-smoke", {}))
    for b in SEARCH_LEGS:
        check(f"qa: live search smoke for {b}", f"BACKEND={b}" in live, "")
    check("qa: live hermes routing smoke", "make hermes-smoke" in live, "")
    check("qa: live model-caps check", "make model-caps" in live, "")
    check("qa: live --require-hits search", "make validate-fetch" in live, "")
    d = jobs.get("dispatch-fixbot", {})
    cond = str(d.get("if", ""))
    check("qa: dispatch-fixbot needs the deterministic validate job",
          d.get("needs") in ("validate", ["validate"]), d.get("needs"))
    check("qa: dispatch-fixbot only on failure", "failure()" in cond, cond)
    check("qa: dispatch-fixbot only for refresh PR branches", "ci/trending-refresh-" in cond, cond)
    check("qa: dispatch-fixbot only for same-repo PRs", "head.repo.full_name" in cond, cond)
    ds = (steps(d) or [{}])[0]
    check("qa: dispatch uses the owner PAT (GITHUB_TOKEN gets HTTP 403)",
          PAT in str(ds.get("env", {}).get("GH_TOKEN", "")), ds.get("env"))
    check("qa: dispatch passes pr_number + branch", "pr_number=" in ds.get("run", "") and "branch=" in ds.get("run", ""), "")
    check("qa: dispatch capped by prior fix-bot commits", "MAX_FIXBOT_COMMITS" in ds.get("run", ""), "")


def test_fix_bot():
    wf = load("fix-bot.yml")
    on = wf["on"]
    check("fix: no workflow_run trigger (double-fire / suppressed for bot PRs)",
          "workflow_run" not in on, list(on))
    check("fix: dispatchable with pr_number + branch",
          {"pr_number", "branch"} <= set((on.get("workflow_dispatch") or {}).get("inputs", {})), "")
    check("fix: one run per PR at a time", "concurrency" in wf, "")
    job = wf["jobs"]["fix"]
    resolve = step(job, "resolve")
    check("fix: refuses master/main", "master|main" in resolve.get("run", ""), "")
    co = step(job, "checkout")
    check("fix: checkout with owner PAT (push re-triggers qa-validate)",
          PAT in str(co.get("with", {}).get("token", "")), co.get("with"))
    rt = run_text(job)
    check("fix: hermes routing smoke before the loop", "make hermes-smoke" in rt, "")
    loop = step(job, "fix loop")
    check("fix: runs scripts/fix_loop.sh", "scripts/fix_loop.sh" in loop.get("run", ""), "")
    check("fix: loop step tolerates a red loop (set +e) and reports green/red",
          "set +e" in loop.get("run", "") and "green=" in loop.get("run", ""), "")
    push = step(job, "commit + push")
    check("fix: push gated on a green loop", "green == 'true'" in str(push.get("if", "")), push.get("if"))
    # The identity comes through ONE seam (issue #325): `make git-identity` sets it from
    # scripts/agent_identity.py, so the step never spells out the name or the address.
    check("fix: the git identity is set before the commit",
          "make git-identity" in push.get("run", ""), push.get("run", "")[:200])
    check("fix: it commits as the repo's own agent, not github-actions[bot]",
          "github-actions" not in push.get("run", "")
          and f'user.email "{AGENT_EMAIL}"' not in push.get("run", ""), push.get("run", "")[:200])
    check("fix: commit message prefix matches qa-validate's cap counter",
          'git commit -m "fix-bot:' in push.get("run", ""), "")
    check("fix: push step has an id (the report reads its outcome)", push.get("id") == "push", push.get("id"))
    rep = step(job, "report result")
    check("fix: result always reported on the PR",
          "always()" in str(rep.get("if", "")) and "gh pr comment" in rep.get("run", ""), "")
    check("fix: report reads the push outcome (never claims 'pushed' after a failed push)",
          "steps.push.outcome" in str(rep.get("env", {})) and "PUSH_OUTCOME" in rep.get("run", ""), rep.get("env"))
    check("fix: qa-report.txt uploaded as an artifact",
          any("upload-artifact" in str(s.get("uses", "")) and "qa-report" in str(s.get("with", {}))
              for s in steps(job)), "")


def _run_push_step(changed: bool) -> tuple[int, str, list[str]]:
    """Execute the REAL fix-bot commit+push script in a temp clone whose
    .gitignore is the repo's, with qa-report.txt + qa-report.txt.notes +
    comment.md present (the loop leaves them behind). Returns (rc, output,
    files in the pushed commit)."""
    import os
    import shutil
    import subprocess
    import tempfile
    push = step(load("fix-bot.yml")["jobs"]["fix"], "commit + push")
    td = Path(tempfile.mkdtemp())
    try:
        g = lambda *a, cwd=None: subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)  # noqa: E731
        g("init", "-q", "--bare", str(td / "remote.git"))
        g("clone", "-q", str(td / "remote.git"), str(td / "wc"))
        wc = td / "wc"
        shutil.copy(ROOT / ".gitignore", wc / ".gitignore")
        (wc / "data.json").write_text("{}\n")
        g("add", "-A", cwd=wc)
        g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base", cwd=wc)
        g("push", "-q", "origin", "HEAD:refs/heads/ci/x", cwd=wc)
        before = g("rev-parse", "HEAD", cwd=wc).stdout.strip()
        (wc / "qa-report.txt").write_text("=== make validate ===\n")
        # The loop's between-round notes used to be written as `$REPORT.notes`
        # (issue #390) — a 0-byte `qa-report.txt.notes` reached PR #387 that way.
        (wc / "qa-report.txt.notes").write_text("=== make fix: TIMED OUT after 1800s ===\n")
        (wc / "comment.md").write_text("c\n")
        if changed:
            (wc / "data.json").write_text('{"fixed": true}\n')
        bin_ = td / "bin"
        bin_.mkdir()
        (bin_ / "sudo").write_text('#!/bin/sh\nexec "$@"\n')
        (bin_ / "sudo").chmod(0o755)
        # The identity seam (issue #325): this clone carries no Makefile (it is a minimal
        # repo on purpose — the PUSH step is what is under test), so the one target the step
        # calls is mapped to the real definition rather than stubbed by hand.
        (bin_ / "make").write_text(
            "#!/bin/sh\n"
            'case "$1" in\n'
            f'  git-identity) exec python3 "{ROOT / "scripts" / "agent_identity.py"}" --git-config ;;\n'
            '  *) echo "unexpected target: $1" >&2; exit 2 ;;\n'
            "esac\n")
        (bin_ / "make").chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", BRANCH="ci/x",
                   GITHUB_OUTPUT=str(td / "out"), HOME=str(td))
        p = subprocess.run(["bash", "-e", "-c", push["run"]], cwd=wc, env=env, capture_output=True, text=True)
        after = g("rev-parse", "refs/heads/ci/x", cwd=td / "remote.git").stdout.strip()
        files = (g("show", "--name-only", "--format=", after, cwd=td / "remote.git").stdout.split()
                 if after != before else [])
        gh_out = (td / "out").read_text() if (td / "out").exists() else ""
        return p.returncode, p.stdout + p.stderr + gh_out, files
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _run_issue_pr_step(issue: str = "376") -> tuple[int, str, str, str]:
    """Execute the REAL issue-bot "Open the PR" step with a stub `gh`.

    Returns (rc, output, the argv gh was called with, the body file it was given).
    The body is what GitHub parses, so it — not the workflow text — is the claim.

    The step now COMPOSES its body through `make pr-body` (issue #287), so it is executed
    in the checkout — the real Makefile recipe and the real composer run — with only `gh`
    (an external system) stubbed. `pr-body.md` is gitignored and removed afterwards.
    """
    import os
    import shutil
    import subprocess
    import tempfile
    pr = step(load("issue-bot.yml")["jobs"]["implement"], "Open the PR")
    td = Path(tempfile.mkdtemp())
    try:
        bin_ = td / "bin"
        bin_.mkdir()
        gh = bin_ / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$*" >> "$TD/gh.log"\n'
            'prev=""\n'
            'for a in "$@"; do\n'
            '  [ "$prev" = "--body-file" ] && cp "$a" "$TD/body.md"\n'
            '  prev="$a"\n'
            "done\n"
            'echo "https://example.invalid/pull/1"\n')
        gh.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ['PATH']}", TD=str(td),
                   ISSUE=issue, BRANCH=f"ci/data-gap-{issue}-slug", REPO="o/r",
                   GH_TOKEN="x", GITHUB_OUTPUT=str(td / "out"))
        # The step's own literal env (e.g. MAKEFLAGS, which keeps make's directory banner
        # out of the body) applies exactly as it does in the job.
        env.update({k: str(v) for k, v in (pr.get("env") or {}).items() if "${{" not in str(v)})
        p = subprocess.run(["bash", "-e", "-c", pr["run"]], cwd=ROOT, env=env,
                           capture_output=True, text=True)
        log = (td / "gh.log").read_text() if (td / "gh.log").exists() else ""
        body = (td / "body.md").read_text() if (td / "body.md").exists() else ""
        return p.returncode, p.stdout + p.stderr, log, body
    finally:
        (ROOT / "pr-body.md").unlink(missing_ok=True)
        shutil.rmtree(td, ignore_errors=True)


def test_issue_bot_pr_body_actually_closes_the_issue():
    """Issue #289: the assertion was `"closes #" in pr_run` — the marker word, not
    the claim. #272's body said `Closes #271 and #276`, closed #271 and left #276
    open, and that check stayed green. The step is now RUN and its body handed to
    the same parser the pipeline uses (scripts/pr_closure.py)."""

    # Given the issue-bot PR step, executed with a stub `gh`
    rc, out, log, body = _run_issue_pr_step("376")

    # Then  it opens the PR with a body FILE (what GitHub reads)
    check("issue-bot: the PR is created with --body-file", rc == 0 and "--body-file" in log, out[-300:] or log)
    check("issue-bot: it hands gh a non-empty body", bool(body.strip()), body[:200])

    # And   that body closes EXACTLY the issue the branch implements
    problems = pr_closure.check(body, "ci/data-gap-376-slug")
    check("issue-bot: the body closes the issue it implements (no chained reference)",
          problems == [], problems)
    binds = pr_closure.closing_bindings(pr_closure.visible_text(body))
    check("issue-bot: exactly one closing keyword, binding one reference",
          binds == [(376, [376])], binds)

    # And   the assertion is not vacuous: the two shapes that broke the pipeline
    #       in reality are still refused by the same parser.
    for bad, why in (("closes #271 and #276", "a chained reference"),
                     ("closes #999", "the wrong issue")):
        check(f"issue-bot: the check would refuse {why}",
              pr_closure.check(bad, "ci/data-gap-376-slug") != [], bad)


def test_fix_bot_announces_its_window():
    """fix-bot announces its repair window on the PR BEFORE it reads the branch (issue #198)."""

    # Given the fix pipeline and its steps, in order
    wf = load("fix-bot.yml")
    job = wf["jobs"]["fix"]
    names = [s.get("name", "") for s in steps(job)]
    announce = step(job, "announce the window")
    announce_at = next((i for i, n in enumerate(names) if "announce the window" in n.lower()), None)
    # The first step that READS the branch is the checkout.
    checkout_at = next((i for i, n in enumerate(names) if n.lower().startswith("checkout")), None)

    # Then  it exists, is posted BEFORE the branch is read, and carries the marker
    check("fix: a start comment announces the repair window", bool(announce), names)
    check("fix: the window opens BEFORE the branch is read",
          announce_at is not None and checkout_at is not None and announce_at < checkout_at,
          f"announce={announce_at} checkout={checkout_at}")
    body = announce.get("run", "")
    check("fix: the marker is the one the shared registry defines",
          "<!-- fix-bot-start:" in body, body[:200])
    check("fix: the start comment names the branch and the run",
          "BRANCH" in body and "GITHUB_RUN_ID" in body, body[:200])
    # The DEFAULT token: the owner PAT is scoped to Actions/Contents/Pull-requests and
    # cannot comment (measured: `Resource not accessible by personal access token
    # (addComment)` on #124).
    check("fix: the announcement uses the default token, not the PAT",
          announce.get("env", {}).get("GH_TOKEN") == "${{ github.token }}", announce.get("env"))
    check("fix: the default token is granted the Issues scope it needs",
          (wf.get("permissions") or {}).get("issues") == "write", wf.get("permissions"))
    # The body arrives on stdin, so no scratch file exists that the push step's
    # `git add -A` could commit.
    check("fix: the announcement writes no file a push could commit",
          "--body-file -" in body and ".md" not in body, body[:300])

    # And the window CLOSES on every path: the outcome comment is `always()` and
    # carries the end marker, so a loop that died mid-way still ends with a stamp.
    rep = step(job, "report result")
    check("fix: the window is closed in the always() outcome comment",
          "always()" in str(rep.get("if", "")) and "<!-- fix-bot-end:" in rep.get("run", ""),
          rep.get("if"))
    check("fix: the end marker carries the run id too",
          "GITHUB_RUN_ID" in rep.get("run", ""), rep.get("run", "")[:200])


def test_fix_bot_push_behaviour():
    """PR #80: the loop went green, then `git add -A -- . ':!qa-report.txt'`
    exited 1 ('paths are ignored by one of your .gitignore files') under
    bash -e, so the fix was never pushed — and the comment still said green."""
    rc, out, files = _run_push_step(changed=True)
    check("fix-push: a green fix is committed and pushed (exit 0)", rc == 0, out[-300:])
    check("fix-push: the pushed commit carries the fix", files == ["data.json"], files)
    check("fix-push: qa-report.txt / comment.md never committed",
          "qa-report.txt" not in files and "comment.md" not in files, files)
    # Issue #390: a SIBLING of the report was committed by the same `git add -A`
    # (an empty qa-report.txt.notes landed in PR #387), so the rule is the whole
    # qa-report.txt.* class, not two exact names.
    check("fix-push: the loop's scratch notes (qa-report.txt.notes) never committed",
          "qa-report.txt.notes" not in files, files)
    check("fix-push: reports pushed=yes", "pushed=yes" in out, out[-200:])
    rc, out, files = _run_push_step(changed=False)
    check("fix-push: green with no changes -> exit 0, nothing pushed", rc == 0 and files == [], (rc, files, out[-200:]))


# The remote-side rejection mirroring GitHub's own rule: a token without
# `workflow` scope may not create or update .github/workflows/**. The text is the
# real message measured on #120 (run 38509118147).
GH_WORKFLOW_HOOK = """#!/bin/sh
refusing() {
  echo "refusing to allow a Personal Access Token to create or update workflow" >&2
  echo "\\`.github/workflows/x.yml\\` without \\`workflow\\` scope" >&2
  exit 1
}
while read -r old new ref; do
  if git ls-tree -r --name-only "$new" 2>/dev/null | grep -q '^\\.github/workflows/'; then
    refusing
  fi
done
exit 0
"""

OTHER_REJECT_HOOK = """#!/bin/sh
echo "error: failed to push some refs to 'origin'" >&2
exit 1
"""


def _run_issue_push(hook: str, touch_workflow: bool) -> tuple[int, str, list[str]]:
    """Execute the REAL issue-bot commit+push script against a REAL bare remote
    whose pre-receive hook rejects like GitHub does. Returns (rc, output, files
    in the pushed commit)."""
    import os
    import shutil
    import subprocess
    import tempfile
    push = step(load("issue-bot.yml")["jobs"]["implement"], "Commit + push")
    td = Path(tempfile.mkdtemp())
    try:
        def g(*a, cwd=None):
            return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
        g("init", "-q", "--bare", str(td / "remote.git"))
        hooks = td / "remote.git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "pre-receive").write_text(hook)
        (hooks / "pre-receive").chmod(0o755)
        g("clone", "-q", str(td / "remote.git"), str(td / "wc"))
        wc = td / "wc"
        shutil.copy(ROOT / ".gitignore", wc / ".gitignore")
        (wc / "data.json").write_text("{}\n")
        g("add", "-A", cwd=wc)
        g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base", cwd=wc)
        g("push", "-q", "origin", "HEAD:refs/heads/master", cwd=wc)
        if touch_workflow:
            (wc / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (wc / ".github" / "workflows" / "x.yml").write_text("name: x\n")
        else:
            (wc / "data.json").write_text('{"impl": true}\n')
        # a scratch artifact the agent left behind (measured on #120)
        (wc / "AGENTS_issue-120.patch").write_text("--- a\n+++ b\n")
        bin_ = td / "bin"
        bin_.mkdir()
        (bin_ / "sudo").write_text('#!/bin/sh\nexec "$@"\n')
        (bin_ / "sudo").chmod(0o755)
        # The step's ONE make call is the branch seam (rule 6n, issue #271). Run the REAL
        # implementation from the repo rather than a stand-in for it: the temp clone is a
        # real clone of a real remote, so `new --in-place` really cuts the branch there.
        (bin_ / "make").write_text(
            "#!/bin/sh\n"
            "# stub `make`: only the branch seam, mapping the target to the real script.\n"
            'case "$1" in\n'
            '  worktree-new|worktree-resume)\n'
            f'    exec python3 "{ROOT / "scripts" / "worktree_base.py"}" "${{1#worktree-}}"'
            ' --branch "$BRANCH" --in-place ;;\n'
            # Issue #500: the commit step adopts the branch and rebases it at COMMIT time.
            '  branch-adopt)\n'
            f'    exec python3 "{ROOT / "scripts" / "worktree_base.py"}" adopt'
            ' --branch "$BRANCH" ;;\n'
            '  base-rebase)\n'
            f'    exec python3 "{ROOT / "scripts" / "worktree_base.py"}" rebase'
            ' --branch "$BRANCH" ;;\n'
            # The identity seam (issue #325): the push step sets the repo-local committer
            # identity through `make git-identity`, which is a plain git config.
            '  git-identity)\n'
            '    git config user.name "Asimov Agent" && git config user.email "support@docondee.com" ;;\n'
            '  *)\n'
            '    echo "stub make: the push step called an unexpected target: $1" >&2; exit 2 ;;\n'
            "esac\n")
        (bin_ / "make").chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", BRANCH="ci/data-gap-120-x",
                   ISSUE="120", GITHUB_OUTPUT=str(td / "out"), HOME=str(td))
        p = subprocess.run(["bash", "-e", "-c", push["run"]], cwd=wc, env=env,
                           capture_output=True, text=True)
        gh_out = (td / "out").read_text() if (td / "out").exists() else ""
        pushed = g("rev-parse", "--verify", "ci/data-gap-120-x", cwd=td / "remote.git")
        files = (g("show", "--name-only", "--format=", pushed.stdout.strip(), cwd=td / "remote.git").stdout.split()
                 if pushed.returncode == 0 else [])
        patch = wc / "issue-implementation.patch"
        if patch.exists():
            files.append(f"PATCH:{patch.read_text().count('diff --git')}")
        return p.returncode, p.stdout + p.stderr + gh_out, files
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_issue_bot_push_scope_rejection():
    """#120 (run 38509118147): the implementation touched .github/workflows/** and
    the push was rejected for the missing `workflow` scope — the run died at
    `git push` with no explanation on the issue. The REAL step must instead: not
    fail on that rejection, report it (scope_error), strip scratch artifacts, and
    still fail on any OTHER push error."""
    rc, out, files = _run_issue_push(GH_WORKFLOW_HOOK, touch_workflow=True)
    check("issue-push: a workflow-scope rejection does NOT fail the step", rc == 0, out[-300:])
    check("issue-push: it reports scope_error=true and pushed=false",
          "scope_error=true" in out and "pushed=false" in out, out[-300:])
    check("issue-push: nothing reached the remote",
          not [f for f in files if not f.startswith("PATCH:")], files)
    check("issue-push: the unpushed implementation is preserved as a patch artifact",
          any(f.startswith("PATCH:") and int(f.split(":")[1]) >= 1 for f in files), files)

    rc, out, files = _run_issue_push(GH_WORKFLOW_HOOK, touch_workflow=False)
    check("issue-push: a normal push still succeeds", rc == 0 and "pushed=true" in out, out[-200:])
    check("issue-push: the pushed commit carries the implementation", "data.json" in files, files)
    check("issue-push: the scratch *.patch is NOT pushed",
          not any(f.endswith(".patch") for f in files), files)

    rc, out, files = _run_issue_push(OTHER_REJECT_HOOK, touch_workflow=False)
    check("issue-push: any OTHER push failure still fails the step", rc != 0, f"rc={rc} {out[-200:]}")


def _deps(jobs: dict, name: str) -> set:
    """All jobs `name` depends on, transitively."""
    out, todo = set(), [name]
    while todo:
        n = jobs[todo.pop()].get("needs", [])
        for d in ([n] if isinstance(n, str) else n):
            if d not in out:
                out.add(d)
                todo.append(d)
    return out


def _guard_ok(run: str) -> bool:
    return ("$OWNER" in run and "$TRIGGER" in run and "$ACTOR" in run
            and "collaborators/$u/permission" in run and "admin|maintain|write)" in run)


def _guard_step(wf_name: str, job: str) -> dict:
    jobs = load(wf_name)["jobs"]
    return next(st for st in steps(jobs[job]) if "guard" in st.get("name", "").lower())


def _run_guard(step: dict, event: str, actor: str, trigger: str, perms: dict) -> tuple[int, str]:
    """Execute the REAL guard script from the workflow YAML with a stub `gh`
    that answers the collaborator-permission API from `perms` (404 -> exit 1)."""
    import os
    import subprocess
    import tempfile
    td = Path(tempfile.mkdtemp())
    table = "\n".join(f"{u}={p}" for u, p in perms.items())
    (td / "perms").write_text(table + "\n")
    gh = td / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
u=$(echo "$2" | sed -E 's#.*/collaborators/([^/]+)/permission#\\1#')
p=$(grep -E "^$u=" "{td}/perms" | cut -d= -f2)
[ -z "$p" ] && {{ echo '{{"message":"Not Found"}}' >&2; exit 1; }}
echo "$p"
""")
    gh.chmod(0o755)
    env = dict(os.environ, PATH=f"{td}:{os.environ['PATH']}", EVENT=event, ACTOR=actor, TRIGGER=trigger,
               OWNER="andyholst", REPO="andyholst/trending-local-llms", GH_TOKEN="x")
    p = subprocess.run(["bash", "-e", "-c", step["run"]], env=env, capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout


AGENT_NAME = _AI.AGENT_NAME
AGENT_EMAIL = _AI.AGENT_EMAIL


def test_every_committing_bot_job_commits_as_the_agent():
    """Issue #323: EVERY job that commits carries the repo's own agent identity.

    `github-actions[bot]` is GitHub's generic automation account, not this repo's
    agent. The repo states its only identities are Andy Holst and Asimov Agent —
    the authorship guard (`scripts/check_commit_authorship.py`, issue #317) reads
    exactly that — yet every committing bot job contradicted it. The old assertion
    named `fix-bot.yml` ALONE and only checked that some `git config` line existed,
    so a job could commit as anyone and stay green.
    """
    # Given every workflow, every job and every step that actually commits
    committing: list[tuple[str, str, str, str]] = []
    for wf in sorted(WF.glob("*.yml")):
        doc = yaml.safe_load(wf.read_text()) or {}
        if True in doc and "on" not in doc:
            doc["on"] = doc.pop(True)
        for job_name, job in (doc.get("jobs") or {}).items():
            for st in steps(job):
                run = st.get("run", "") or ""
                if "git commit" in run:
                    committing.append((wf.name, job_name, st.get("name", ""), run))

    # Then the set is non-empty (a guard that finds nothing proves nothing)…
    check("identity: the committing bot jobs are found", bool(committing), len(committing))

    # …and each one sets the agent identity, and never the generic bot account.
    for wf_name, job_name, step_name, run in committing:
        where = f"{wf_name} {job_name} / {step_name}"
        # Issue #325: the identity is consumed through ONE seam (`make git-identity`), so a new
        # committing job inherits it and a change to the address is a one-line edit — instead of
        # the same two `git config` lines hand-kept in four workflows.
        check(f"identity: {where} sets the identity through the one seam",
              "make git-identity" in run, run[:220])
        check(f"identity: {where} does not carry the identity as a literal",
              f'git config user.email "{AGENT_EMAIL}"' not in run, run[:220])
        check(f"identity: {where} does not commit as github-actions[bot]",
              "github-actions" not in run, run[:220])



def test_the_agent_identity_has_one_definition():
    """Issue #325: the identity was five hand-kept copies of one fact — the same two `git
    config` lines in four workflows plus the authorship guard's own allowed set. Nothing
    derived one from the other, so a new committing workflow copies whatever it finds."""
    check("identity: the agent email is in the allowed set",
          AGENT_EMAIL in _AI.ALLOWED_EMAILS, _AI.ALLOWED_EMAILS)
    check("identity: the agent name is in the allowed set",
          AGENT_NAME.lower() in _AI.ALLOWED_NAMES, _AI.ALLOWED_NAMES)
    # …and the guard reads the SAME definition rather than keeping its own copy.
    import check_commit_authorship as CCA
    check("identity: the authorship guard's emails ARE the one definition",
          tuple(CCA.ALLOWED_EMAILS) == tuple(_AI.ALLOWED_EMAILS), CCA.ALLOWED_EMAILS)
    check("identity: the authorship guard's names ARE the one definition",
          tuple(CCA.ALLOWED_NAMES) == tuple(_AI.ALLOWED_NAMES), CCA.ALLOWED_NAMES)
    # The workflows never spell it out.
    offenders = [f.name for f in sorted(WF.glob("*.yml"))
                 if AGENT_EMAIL in f.read_text() or f'user.name "{AGENT_NAME}"' in f.read_text()]
    check("identity: no workflow carries the identity literally", not offenders, offenders)
    # …and the seam itself exists and calls the script.
    mk = (ROOT / "Makefile").read_text()
    check("identity: `make git-identity` runs the one definition",
          "python3 scripts/agent_identity.py --git-config" in mk, "")
    check("identity: the seam is a host target (git config is host-side)",
          "git-identity:\n\t$(MAKE) _git-identity" in mk, "")


def test_owner_guards():
    """#67: every refresh-bot job is gated by a guard that allows ONLY the
    owner or a collaborator with write/maintain/admin (for the actor AND the
    triggering actor, so re-runs are covered); aggregate can't run on a
    refused guard; fix-bot checks before any step that touches a secret."""
    wf = load("refresh-bot.yml")
    jobs = wf["jobs"]
    g = jobs.get("guard", {})
    gstep = (steps(g) or [{}])[0]
    genv = gstep.get("env", {})
    check("access: refresh-bot has a 'guard' job", bool(g), list(jobs))
    check("access: guard checks actor AND triggering_actor: owner or write+ collaborator",
          "github.actor" in str(genv.get("ACTOR")) and "github.triggering_actor" in str(genv.get("TRIGGER"))
          and "repository_owner" in str(genv.get("OWNER")) and _guard_ok(gstep.get("run", "")), genv)
    check("access: guard lets the daily schedule through", '"schedule"' in gstep.get("run", ""))
    check("access: guard uses env, not inline ${{ }} in the script (no injection)",
          "${{" not in gstep.get("run", ""))
    for name in jobs:
        if name != "guard":
            check(f"access: refresh-bot job '{name}' depends on guard", "guard" in _deps(jobs, name), _deps(jobs, name))
    cond = str(jobs["aggregate"].get("if", ""))
    check("access: aggregate requires guard success (not bare always())",
          "needs.guard.result == 'success'" in cond, cond)
    check("access: aggregate requires build success", "needs.build.result == 'success'" in cond, cond)
    conc = wf.get("concurrency", {})
    check("concurrency: refresh-bot runs queue (group set, no cancel)",
          bool(conc.get("group")) and conc.get("cancel-in-progress") is False, conc)

    fb = load("fix-bot.yml")["jobs"]
    g = fb.get("guard", {})
    gstep = (steps(g) or [{}])[0]
    genv = gstep.get("env", {})
    check("access: fix-bot's guard is its OWN first job (issue #259)", bool(g), list(fb))
    check("access: fix-bot's guard checks actor AND triggering_actor: owner or write+ collaborator",
          "github.triggering_actor" in str(genv.get("TRIGGER")) and _guard_ok(gstep.get("run", "")))
    check("access: fix-bot's guard declares no secret at job level (rule 6j)",
          "secrets." not in str(g.get("env", {})), g.get("env"))
    check("access: fix-bot's guard step touches no secret",
          not [st for st in steps(g) if "secrets." in str(st)], steps(g))
    for name in fb:
        if name != "guard":
            check(f"access: fix-bot job '{name}' needs the guard", "guard" in _deps(fb, name), _deps(fb, name))
    check("access: fix-bot's secret-carrying job declares its secrets at job level",
          "secrets." in str(fb["fix"].get("env", {})), fb["fix"].get("env"))


#: Every bot pipeline's guard, and the job whose guard step it is (issue #238).
#: `qa-validate` is here too (issue #279): its guard admits `pull_request`/`push`
#: — repository events GitHub starts for the repo itself — and guards only the
#: 30-minute, network-bound dispatch.
BOT_GUARDS = (
    ("refresh-bot.yml", "guard"),
    ("fix-bot.yml", "guard"),
    ("issue-bot.yml", "guard"),
    ("issue-review-bot.yml", "guard"),
    ("publish-agent-image.yml", "guard"),
    ("qa-validate.yml", "guard"),
    ("code-review-bot.yml", "guard"),
    ("queued-alarm.yml", "guard"),
    ("pr-health.yml", "guard"),
    ("pr-closure.yml", "guard"),
    ("architecture-bot.yml", "guard"),
)

#: Events a guard must admit WITHOUT asking who called, because GitHub starts
#: them for the repository itself (there is no caller to admit).
REPO_EVENTS = ("pull_request", "push")

#: The caller classes every bot guard must decide the same way (issue #238). The
#: bot itself is a bot-to-bot dispatch with the default token; it MUST be allowed.
GUARD_CALLERS = (
    ("workflow_dispatch", "andyholst", "andyholst", 0, "owner dispatch"),
    ("workflow_dispatch", "alice", "alice", 0, "write collaborator"),
    ("workflow_dispatch", "bob", "bob", 0, "maintain collaborator"),
    ("workflow_dispatch", "carol", "andyholst", 0, "admin collaborator re-run of owner run"),
    ("workflow_dispatch", "github-actions[bot]", "github-actions[bot]", 0, "the bot itself"),
    ("workflow_dispatch", "eve", "eve", 1, "read-only collaborator"),
    ("workflow_dispatch", "mallory", "mallory", 1, "triage collaborator"),
    ("workflow_dispatch", "stranger", "stranger", 1, "non-collaborator (API 404)"),
    ("workflow_dispatch", "andyholst", "stranger", 1, "stranger re-running an owner run"),
)

GUARD_PERMS = {"alice": "write", "bob": "maintain", "carol": "admin", "eve": "read", "mallory": "triage"}


def _guard_step_index(wf_name: str) -> tuple[str, int] | None:
    """(job, index) of this workflow's trigger guard, derived from the TREE.

    The shape is the one `_guard_step` already detects — a step whose NAME
    carries `guard` — but found by scanning, so a guard nobody registered is
    still FOUND instead of being invisible (issue #313).
    """
    for job_name, body in (load(wf_name).get("jobs") or {}).items():
        if not isinstance(body, dict):
            continue
        for i, st in enumerate(steps(body)):
            if "guard" in str(st.get("name", "")).lower():
                return job_name, i
    return None


def discovered_guards() -> dict[str, str]:
    """Every workflow in the tree that carries a guard step -> the job it is in."""
    found: dict[str, str] = {}
    for f in sorted(WF.glob("*.yml")):
        hit = _guard_step_index(f.name)
        if hit:
            found[f.name] = hit[0]
    return found


def _dispatchable(wf_name: str) -> bool:
    """Whether the workflow can be started by hand (`workflow_dispatch`)."""
    on = load(wf_name).get("on") or {}
    return isinstance(on, dict) and "workflow_dispatch" in on


def _has_cron(wf_name: str) -> bool:
    """Whether the workflow declares an `on.schedule` cron."""
    return re.search(r"^\s{2}schedule:\s*$", (WF / wf_name).read_text(), re.M) is not None


def test_guard_behaviour():
    """Run the REAL guard scripts of EVERY bot pipeline for every caller class
    (issue #238): the owner, a write+ collaborator AND github-actions[bot] (the bot
    itself) are allowed; a read/triage collaborator, a non-collaborator and a
    stranger re-running an owner run are refused."""
    for wf_name, job in BOT_GUARDS:
        step = _guard_step(wf_name, job)
        for event, actor, trigger, want, label in GUARD_CALLERS:
            rc, out = _run_guard(step, event, actor, trigger, GUARD_PERMS)
            verdict = "allowed" if want == 0 else "refused"
            check(f"guard {wf_name}: {label} -> {verdict}", (rc == 0) == (want == 0),
                  f"rc={rc} {out.strip()[-120:]}")


def test_guard_is_before_any_secret():
    """#259: the guard must sit before ANY secret, and the only checkable form of that is a guard
    JOB that declares no secret at all — because a job-level `env:` holding `secrets.*` is
    materialised when the JOB starts. A guard that is merely the first STEP of the
    secret-carrying job satisfies no step-level assertion and can drift further with no red
    (the original fix-bot shape: four secrets at job level, the guard a step under them)."""
    for wf_name, job in BOT_GUARDS:
        jobs = load(wf_name)["jobs"]
        g = jobs.get(job, {})
        check(f"guard {wf_name}: the guard is its own job named '{job}'", job in jobs, list(jobs))
        check(f"guard {wf_name}: the guard job declares no secret at job level",
              "secrets." not in str(g.get("env", {})), g.get("env"))
        secret_steps = [i for i, st in enumerate(steps(g)) if "secrets." in str(st)]
        check(f"guard {wf_name}: no guard step touches a secret", not secret_steps, secret_steps)
        gdeps = _deps(jobs, job) if job in jobs else {job}
        check(f"guard {wf_name}: the guard job needs nothing", not gdeps, gdeps)
        for name in jobs:
            if name != job:
                check(f"guard {wf_name}: job '{name}' runs only after the guard",
                      job in _deps(jobs, name), f"needs={jobs[name].get('needs')}")


def test_every_bot_guard_with_a_cron_has_the_schedule_bypass():
    """A cron bot's scheduled run must not depend on which identity GitHub
    attributes it to (issue #238): its guard carries the schedule bypass, and a
    scheduled run attributed to github-actions[bot] is allowed."""
    for wf_name, job in BOT_GUARDS:
        if not _has_cron(wf_name):
            continue
        step = _guard_step(wf_name, job)
        check(f"guard {wf_name}: a cron bot carries the schedule bypass",
              '"schedule"' in step["run"], step["run"][:80])
        rc, out = _run_guard(step, "schedule", "github-actions[bot]", "github-actions[bot]", GUARD_PERMS)
        check(f"guard {wf_name}: a scheduled run is allowed", rc == 0, out.strip()[-120:])


def test_the_guard_registry_is_derived_from_the_tree():
    """Issue #313: `BOT_GUARDS` must be the RECORD of the guard decision, never
    the INPUT to the tests that exercise it. A literal tuple is remembered, and
    what is remembered gets forgotten — measured: `code-review-bot.yml` and
    `queued-alarm.yml` carried guards that `ARCHITECTURE.md` described and no
    test ever ran, and `fix-bot.yml`'s entry named the `fix` job while the guard
    lived elsewhere. The suite was green through all of it, because a pipeline
    that is missing from the registry is simply not in the "N passed".

    So the tree is the input and the registry is checked against it, in BOTH
    directions: a guard nobody registered fails, and a registered pipeline that
    lost its guard fails.
    """
    discovered = discovered_guards()
    registered = dict(BOT_GUARDS)

    check("guards: the tree yields guarded pipelines (the guard is not vacuous)",
          bool(discovered), discovered)

    # Direction 1: a guarded workflow that is not registered — the guard would
    # never be exercised by any caller-class test.
    unregistered = sorted(set(discovered) - set(registered))
    check("guards: every workflow carrying a guard step is in BOT_GUARDS",
          not unregistered, unregistered)

    # Direction 2: a registered pipeline whose guard is gone.
    vanished = sorted(set(registered) - set(discovered))
    check("guards: every registered pipeline still carries its guard step",
          not vanished, vanished)

    # …and they must agree about WHICH job the guard is in (fix-bot's measured
    # drift: the registry named `fix`, the guard was not the first step of it).
    mismatched = {n: (registered[n], discovered[n])
                  for n in sorted(set(registered) & set(discovered)) if registered[n] != discovered[n]}
    check("guards: BOT_GUARDS names the job each guard is actually in",
          not mismatched, mismatched)

    # The direction that protects the keys: a workflow that can be DISPATCHED
    # must be guarded, or someone's manual start is the unguarded one.
    undefended = [f.name for f in sorted(WF.glob("*.yml"))
                  if _dispatchable(f.name) and f.name not in discovered]
    check("guards: every dispatchable workflow carries a guard", not undefended, undefended)


def _declares_repo_events(wf_name: str) -> list[str]:
    """Which repository events this workflow declares in its `on:` block."""
    on = load(wf_name).get("on") or {}
    if not isinstance(on, dict):
        return []
    return [e for e in REPO_EVENTS if e in on]


def test_a_repo_event_run_is_admitted_by_its_guard():
    """A `pull_request`/`push` run is started by GitHub for the repository
    itself — there is no caller to admit — so a pipeline that declares one must
    admit it whatever the actor (issue #279). The only such pipeline today is
    `qa-validate`, whose PRs must be validated whatever their author: a guard
    that refused them would leave every outside PR red for ever."""
    found = 0
    for wf_name, job in BOT_GUARDS:
        events = _declares_repo_events(wf_name)
        if not events:
            continue
        step = _guard_step(wf_name, job)
        for ev in events:
            found += 1
            rc, out = _run_guard(step, ev, "stranger", "stranger", {})
            check(f"guard {wf_name}: a {ev} run by a stranger is admitted", rc == 0,
                  out.strip()[-120:])
    check("a repo-event guard was found (non-vacuous)", found > 0, found)


def test_a_guarded_pipeline_gates_the_jobs_that_read_secrets():
    """The guard runs BEFORE anything reads a secret, and the jobs that carry a
    secret need it (issue #279): a guard in a parallel job — or after the first
    secret — guards nothing."""
    for wf_name, job in BOT_GUARDS:
        jobs = load(wf_name)["jobs"]
        steps_ = steps(jobs[job])
        guard_at = [i for i, s in enumerate(steps_)
                    if "guard" in str(s.get("name", "")).lower()]
        check(f"{wf_name}: the guard is the FIRST step of {job}",
              guard_at == [0], guard_at)
        if "guard" in jobs and job != "guard":
            check(f"{wf_name}: the guard job needs nothing (it runs first)",
                  not (jobs["guard"].get("needs") or []), jobs["guard"].get("needs"))
            needs = {n for n, j in jobs.items() if "guard" in (j.get("needs") or [])}
            check(f"{wf_name}: at least one job needs the guard", needs, list(jobs))
def test_bot_verification_protocol_is_documented_and_guarded():
    """The one-bot-at-a-time verification protocol is a RULE, not prose
    (AGENTS.md is the rulebook, rule 2/§8): the document carries it, and the
    guard it mandates is exactly the one `BOT_GUARDS` proves for every pipeline.
    A protocol nothing can check rots the moment someone reorders a job."""
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    # The protocol itself: one bot per cycle, and one bot at a time on the way back
    check("AGENTS.md: carries the bot verification protocol",
          "**Bot verification protocol" in agents, "")
    check("AGENTS.md: ONE bot per cycle, never several at once",
          "ONE bot per cycle, never several at" in agents, "")
    check("AGENTS.md: the fix PR carries the regression guard that catches the defect",
          "the regression guard that would" in agents, "")
    check("AGENTS.md: no PR is verified before it is MERGED",
          "until it is MERGED" in agents, "")
    check("AGENTS.md: a PR lands only through auto-merge, never --admin",
          "NEVER `--admin`" in agents, "")
    check("AGENTS.md: verification re-dispatches each bot on its own",
          "one at a time: re-dispatch each merged bot" in agents, "")
    # The guard the protocol mandates: FIRST job, actor AND triggering actor
    check("AGENTS.md: the guard is the FIRST job on BOTH actor and triggering_actor",
          "FIRST job admits" in agents and "`github.actor` and `github.triggering_actor`" in agents,
          "")
    check("AGENTS.md: the guard identity set is owner / write+ / the bot",
          "`write`/`maintain`/`admin`" in agents and "`github-actions[bot]`" in agents, "")
    # …and the machinery matches the promise: the guard is the first step of the
    # job that carries it, in EVERY pipeline the protocol names.
    for wf_name, job_name in BOT_GUARDS:
        job_steps = steps(load(wf_name)["jobs"][job_name])
        at = [i for i, s in enumerate(job_steps) if "guard" in str(s.get("name", "")).lower()]
        check(f"protocol: {wf_name}'s guard is the FIRST step of `{job_name}`", at == [0], at)


def test_nothing_pushes_master():
    for f in sorted(WF.glob("*.yml")):
        t = f.read_text()
        bad = [l.strip() for l in t.splitlines()
               if "git push" in l and ("master" in l or "main" in l)]
        check(f"no-master: {f.name} never pushes master/main", not bad, bad)
        jobs = load(f.name).get("jobs", {})
        mergers = sorted(n for n, j in jobs.items() if "gh pr merge" in run_text(j))
        allowed = ["auto-merge"] if f.name == "qa-validate.yml" else []
        check(f"no-master: {f.name} merges a PR only from qa-validate's auto-merge job",
              mergers == allowed, mergers)


def test_auto_merge():
    """Green PR -> squash-merge + delete branch. Must never merge a red, stale,
    draft or fork PR, and must merge as the owner (PAT) so master CI runs."""
    jobs = load("qa-validate.yml")["jobs"]
    am = jobs.get("auto-merge", {})
    needs = am.get("needs", [])
    needs = [needs] if isinstance(needs, str) else needs
    check("auto-merge: needs validate AND live-smoke", {"validate", "live-smoke"} <= set(needs), needs)
    cond = str(am.get("if", ""))
    check("auto-merge: only when every needed job succeeded", "success()" in cond
          and "always()" not in cond and "failure()" not in cond, cond)
    check("auto-merge: only on pull_request events", "github.event_name == 'pull_request'" in cond, cond)
    check("auto-merge: never a draft PR", "draft == false" in cond, cond)
    check("auto-merge: only same-repo PRs (no forks)", "head.repo.full_name == github.repository" in cond, cond)
    check("auto-merge: never from master/main", "'master'" in cond and "'main'" in cond, cond)
    st = step(am, "merge")
    run = st.get("run", "")
    check("auto-merge: uses the owner PAT (GITHUB_TOKEN merge starts no master CI)",
          PAT in str(st.get("env", {}).get("GH_TOKEN", "")), st.get("env"))
    check("auto-merge: squash-merges", "gh pr merge" in run and "--squash" in run, run)
    check("auto-merge: deletes the feature branch", "--delete-branch" in run, run)
    check("auto-merge: merges only the validated head commit",
          "--match-head-commit" in run and "pull_request.head.sha" in str(st.get("env", {})), run)
    check("auto-merge: never --admin (bypasses checks)", "--admin" not in run, run)
    check("auto-merge: one merge attempt per PR at a time", bool(am.get("concurrency")), am.get("concurrency"))


def test_issue_bot_scrubs_the_agent_stream_before_it_reaches_the_log():
    """#351: the implement step's agent stream IS the step's console log, so it is captured to a
    gitignored file and only `make scrub-log`'s bounded, REDACTED tail is printed; the run artifact
    is the REDACTED log. A capture without the redactor is a leak surface (the guard refuses it),
    and the refusal contract — a non-zero rc from `make implement-issue` fails the run — is
    unchanged."""
    wf = load("issue-bot.yml")
    impl_steps = steps(wf["jobs"]["implement"])
    step = next((s for s in impl_steps if s.get("id") == "impl"), None)
    check("issue-bot: the implement step exists", step is not None,
          [s.get("name") for s in impl_steps])
    run = str((step or {}).get("run", ""))
    check("issue-bot: the agent stream is CAPTURED, not printed",
          "make implement-issue > implement.log 2>&1" in run, run[:200])
    check("issue-bot: the capture is redacted in the SAME step",
          "make scrub-log FILE=implement.log" in run, run[:200])
    check("issue-bot: the raw capture is never printed by the step",
          "cat implement.log" not in run and "tail -" not in run, run[:200])
    check("issue-bot: the reported tail is bounded", "TAIL=" in run, run[:200])
    check("issue-bot: the refusal contract is unchanged (rc captured, false → red)",
          'echo "rc=$rc" >> "$GITHUB_OUTPUT"' in run and "implemented=false" in run, run[:400])

    arts = [s for s in impl_steps if "upload-artifact" in str(s.get("uses", ""))]
    paths = " ".join(str(s.get("with", {}).get("path", "")) for s in arts)
    check("issue-bot: the REDACTED log is the artifact", "implement.scrubbed.log" in paths, paths)
    check("issue-bot: the RAW log is never uploaded",
          "implement.log" not in paths.replace("implement.scrubbed.log", ""), paths)

    resets = [str(s.get("run", "")) for s in impl_steps if "git reset -q --" in str(s.get("run", ""))]
    check("issue-bot: the capture is reset out of every commit", resets and all("implement.log" in r for r in resets),
          len(resets))
    check("issue-bot: the capture is gitignored", "implement.log" in (ROOT / ".gitignore").read_text(), "")


def test_issue_bot():
    """#113: the implementer bot reacts ONLY to a newly-created data-gap issue,
    ONE implementer per issue, and it owns its own PR's pipeline: implement ->
    push -> PR (closes the issue) -> fix loop -> push when green. It never merges
    and never pushes master (the pipeline that created the PR must go green)."""
    wf = load("issue-bot.yml")
    trig = wf.get("on") or wf.get(True) or {}
    jobs = wf["jobs"]

    check("issue-bot: triggers on issues opened", (trig.get("issues") or {}).get("types") == ["opened"], trig.get("issues"))
    # The surface is `issues: [opened]` + the backlog sweep + owner dispatch —
    # never a PR, a comment, a push or a workflow_run (workflow_run double-fired
    # and was suppressed before, and a PR/comment is not an issue to implement).
    check("issue-bot: no PR/comment/push/workflow_run trigger",
          not ({"pull_request", "pull_request_target", "issue_comment", "workflow_run", "push"} & set(trig)),
          list(trig))
    check("issue-bot: its only event triggers are issues, schedule and dispatch",
          set(trig) == {"issues", "schedule", "workflow_dispatch"}, list(trig))
    check("issue-bot: owner dispatch takes an issue number",
          "issue_number" in str(trig.get("workflow_dispatch", {})), trig.get("workflow_dispatch"))

    g = jobs.get("guard", {})
    gstep = (steps(g) or [{}])[0]
    check("issue-bot: has a guard job whose FIRST step is the trigger guard",
          bool(g) and "guard" in gstep.get("name", "").lower(), gstep.get("name"))
    check("issue-bot: guard checks actor AND triggering_actor: owner or write+ collaborator",
          "github.actor" in str(gstep.get("env", {}).get("ACTOR"))
          and "github.triggering_actor" in str(gstep.get("env", {}).get("TRIGGER"))
          and _guard_ok(gstep.get("run", "")), gstep.get("env"))
    check("issue-bot: guard uses env, not inline ${{ }} (no injection)",
          "${" + "{" not in gstep.get("run", ""))
    check("issue-bot: implement depends on guard", "guard" in _deps(jobs, "implement"), _deps(jobs, "implement"))

    impl = jobs["implement"]
    cond = str(impl.get("if", ""))
    check("issue-bot: reacts only to a NEWLY-created issue (action == opened)", "action == 'opened'" in cond, cond)
    check("issue-bot: ignores an issue without the analysis label",
          "data-gap-analysis" in cond and "labels" in cond, cond)
    check("issue-bot: the owner may dispatch it", "workflow_dispatch" in cond, cond)
    secret_steps = [i for i, st in enumerate(steps(impl)) if "secrets." in str(st)]
    check("issue-bot: every secret-using step is AFTER the guard job (guard is a separate job)",
          bool(g) and all("secrets." not in str(st) for st in steps(g)), secret_steps)

    conc = wf.get("concurrency", {})
    check("issue-bot: one implementer per issue (concurrency keyed by the issue number)",
          "issue.number" in str(conc.get("group")) and conc.get("cancel-in-progress") is False, conc)

    body = run_text(impl)
    check("issue-bot: implements through make (never a raw hermes invocation in the workflow)",
          "make implement-issue" in body and "hermes -z" not in body, "")
    check("issue-bot: checks the issue is still OPEN before implementing", ".state" in body, "")
    check("issue-bot: one branch per issue (ci/data-gap-<n>-<slug>)", "ci/data-gap-" in body, "")
    # Issue #500: attaching an existing branch moved INTO `branch-adopt` (the script fetches the
    # remote branch and checks it out), so the step no longer spells `ls-remote` itself — the
    # contract here is that it goes through that seam and never force-pushes.
    check("issue-bot: a re-run attaches the issue's branch through the seam, never a force-push",
          "make branch-adopt" in body and "--force" not in body, "")
    check("issue-bot: the branch goes through the Makefile seam, never a bare checkout",
          "make branch-adopt" in body and "make base-rebase" in body
          and 'git checkout "$BRANCH"' not in body and 'git checkout -b "$BRANCH"' not in body, "")
    check("issue-bot: commits + pushes the implementation", "git commit" in body and "git push -u origin" in body, "")

    pr = step(impl, "Open the PR")
    pr_run = pr.get("run", "")
    check("issue-bot: opens the PR against master", "--base master" in pr_run, pr_run[:200])
    # The old check here was `"closes #" in pr_run` — a marker word, which is
    # exactly what hid #272 (`Closes #271 and #276` closed only #271). The body
    # the step really hands to `gh` is now checked with the pipeline's own
    # parser; see test_issue_bot_pr_body_actually_closes_the_issue (#289).
    check("issue-bot: opens the PR with the owner PAT (a GITHUB_TOKEN PR is held for approval)",
          PAT in str(pr.get("env", {}).get("GH_TOKEN", "")), pr.get("env"))
    check("issue-bot: never merges a PR itself", "gh pr merge" not in body, "")

    loop = step(impl, "Fix loop")
    check("issue-bot: monitors the pipeline it created (the real fix loop)",
          "scripts/fix_loop.sh" in loop.get("run", ""), loop.get("run", "")[:200])
    push = step(impl, "Push the fixes")
    check("issue-bot: pushing the fixes is gated on the loop being green",
          "green == 'true'" in str(push.get("if", "")), push.get("if"))
    check("issue-bot: reports the outcome on the issue (branch, PR, green)",
          "issue comment" in run_text(impl), "")

    check("issue-bot: guard job runs before any secret-bearing job",
          "guard" in _deps(jobs, "implement"), _deps(jobs, "implement"))

    # The first REAL run (#124, run 38502619350) failed twice, and both failures
    # are guardable:
    #  1. `make implement-issue` ran hermes WITHOUT `_setup` in the same
    #     container, so the `nous-deepseek` alias did not exist and Hermes
    #     auto-routed to HF_TOKEN -> `HTTP 403 ... Inference Providers`;
    #  2. the outcome comment used the owner PAT, which has no Issues write ->
    #     `GraphQL: Resource not accessible by personal access token (addComment)`.
    mk = (ROOT / "Makefile").read_text()
    recipe = re.search(r"\nimplement-issue:\n((?:\t[^\n]*\n)+)", mk)
    body = recipe.group(1) if recipe else ""
    check("issue-bot: `make implement-issue` runs `_setup` in the SAME container as the hermes call",
          "_setup" in body and "_implement-issue" in body, body[:200])
    # Structural, not a character window: the flag must be in the `_implement-issue`
    # RECIPE itself. The old check sliced 4000 chars after the first mention of
    # `_implement-issue:` (which also appears in `implement-issue`'s comment), so a
    # longer prompt pushed the flag out of the window and went red with the alias
    # perfectly intact — a guard that measured the file's LENGTH, not the alias.
    import re as _re
    hermes_recipe = _re.search(r"\n_implement-issue:\n((?:\t[^\n]*\n)+)", mk)
    hermes_body = hermes_recipe.group(1) if hermes_recipe else ""
    # The alias is the Makefile's ONE definition (issue #221): the recipe uses
    # `$(HERMES_ALIAS)`, so the check reads the variable the image config is built from.
    check("issue-bot: the `_implement-issue` recipe is the alias-using one",
          "-m $(HERMES_ALIAS)" in hermes_body, hermes_body[:300])
    comment = step(impl, "Report the outcome")
    check("issue-bot: the outcome comment uses the default token (the PAT has no Issues write)",
          comment.get("env", {}).get("GH_TOKEN") == "${{ github.token }}", comment.get("env"))
    resolve = step(impl, "Resolve the issue")
    check("issue-bot: issue reads use the default token too",
          resolve.get("env", {}).get("GH_TOKEN") == "${{ github.token }}", resolve.get("env"))
    check("issue-bot: the PR step still uses the owner PAT (a GITHUB_TOKEN PR is held for approval)",
          PAT in str(step(impl, "Open the PR").get("env", {}).get("GH_TOKEN", "")))
    # Sweep the existing backlog (#127): an HOURLY run implements ONE open
    # labelled issue that no implementer has touched yet. Hourly rather than
    # 6-hourly: the sweep takes ONE issue per run, so a backlog of N gap issues
    # (the analysis can file several in a day) otherwise waits up to 6 h per
    # issue, and an empty sweep is a green no-op either way. #163 sat unlabelled
    # for 5 h with nobody to pick it up — the cadence is what bounds that.
    sched = trig.get("schedule")
    crons = [str(s.get("cron", "")) for s in (sched if isinstance(sched, list) else [])]
    check("issue-bot: sweeps the backlog hourly",
          "19 * * * *" in crons, sched)
    check("issue-bot: the sweep never sits on the hour (GitHub delays/drops those crons)",
          bool(crons) and all(c.split()[0] != "0" for c in crons), crons)
    pick = jobs.get("pick", {})
    check("issue-bot: the picker needs the guard", "guard" in _deps(jobs, "pick"), _deps(jobs, "pick"))
    pick_if = str(pick.get("if", ""))
    check("issue-bot: the picker runs for the cron OR a dispatch with no issue number",
          "github.event_name == 'schedule'" in pick_if
          and "workflow_dispatch" in pick_if and "inputs.issue_number == ''" in pick_if, pick_if)
    sweep_branches = [p for p in cond.split("||") if "issue_number == ''" in p]
    check("issue-bot: the sweep branch (cron or empty dispatch) requires a picked issue",
          bool(sweep_branches) and all("needs.pick.outputs.issue != ''" in p for p in sweep_branches),
          sweep_branches)
    pick_run = run_text(pick)
    # The RULE (oldest open labelled issue, no implementer, no live reviewer
    # window) has ONE home now — scripts/issue_queue.py, read by both bots — so
    # this test asserts the WIRING and tests/test_issue_review.py asserts the rule
    # itself (rule 6d: a second copy is the defect, not a second assertion).
    check("issue-bot: the picker reads the producer's OWN pick line, not a sed of its row",
          "make issue-pick" in pick_run and "issue list" not in pick_run
          and "matching-refs" not in pick_run and "sed -n 's/^issue=" not in pick_run,
          pick_run[:300])
    check("issue-bot: the queue's own test file runs in the suite",
          wired(ROOT / "tests" / "test_issue_review.py"), "")
    check("issue-bot: an empty backlog is a green run that implements nothing",
          'issue=' in pick_run and "backlog empty" in pick_run, "")
    # The reviewer's verdict is a HOLD, and the sweep says so on the issue
    # (issue #200): it runs `make issue-skip-note` with the default token (the owner
    # PAT cannot comment) and edits no label — the verdict belongs to the reviewer.
    # Issue #202: the note runs on EVERY sweep, never only when the pick came back
    # empty — a sweep that takes one issue still skipped every other held one, and a
    # gate on the pick made those holds silent for ever.
    verdict_step = step(pick, "Note a fresh reviewer verdict")
    check("issue-bot: a fresh verdict is noted on the issue (make issue-skip-note)",
          "make issue-skip-note" in verdict_step.get("run", ""), verdict_step)
    check("issue-bot: the note runs on EVERY sweep, not only when the pick found nothing",
          "outputs.issue" not in str(verdict_step.get("if", "")), verdict_step.get("if"))
    check("issue-bot: the note uses the default token (the PAT cannot comment)",
          verdict_step.get("env", {}).get("GH_TOKEN") == "${{ github.token }}", verdict_step.get("env"))
    check("issue-bot: the note never edits a label",
          not re.search(r"gh (issue )?edit|\blabel\b", verdict_step.get("run", "")), verdict_step.get("run"))
    check("issue-bot: the verdict step is part of the ONE pick job",
          verdict_step in steps(pick), "")
    check("issue-bot: the picker exposes the chosen issue number",
          "issue" in pick.get("outputs", {}), pick.get("outputs"))
    check("issue-bot: implement needs the picker and honours a skipped pick",
          "pick" in _deps(jobs, "implement") and "always()" in cond, cond)
    check("issue-bot: schedule path also requires a picked issue",
          "needs.pick.outputs.issue != ''" in cond, cond)
    job_conc = impl.get("concurrency", {})
    check("issue-bot: ONE implementer per issue across paths (job-level group keyed by the issue)",
          "issue-bot-issue-" in str(job_conc.get("group"))
          and "needs.pick.outputs.issue" in str(job_conc.get("group"))
          and job_conc.get("cancel-in-progress") is False, job_conc)
    check("issue-bot: the sweep reuses the ONE implement job (no second implementation path)",
          sum(1 for j in jobs.values() if "make implement-issue" in run_text(j)) == 1, "")

    # Measured on #120 (run 38509118147): the implementation touched
    # .github/workflows/** and the push was rejected —
    # "refusing to allow a Personal Access Token to create or update workflow …
    # without `workflow` scope". That is a TOKEN problem: it must be detected,
    # explained on the issue, and made red ON PURPOSE (not die at `git push`).
    push_step = step(impl, "Commit + push")
    push_run = push_step.get("run", "")
    check("issue-bot: the push detects the workflow-scope rejection",
          "refusing to allow a Personal Access Token" in push_run and "scope_error=true" in push_run, "")
    check("issue-bot: a scope rejection does not die at git push (it is reported)",
          "exit 0" in push_run.split("scope_error=true")[1][:200], push_run[-200:])
    check("issue-bot: any OTHER push failure still fails the step",
          "::error::git push failed" in push_run, "")
    check("issue-bot: scratch artifacts (*.patch/*.rej/*.orig) are never committed",
          "*.patch" in push_run and "git rm -q --cached" in push_run, "")
    # …and when the push IS rejected, the committed work is attached so it is not
    # thrown away with the ephemeral runner (the file itself is proven to be
    # produced by test_issue_bot_push_scope_rejection).
    upload = step(impl, "Upload the unpushed implementation")
    check("issue-bot: ANY rejected push uploads the implementation as an artifact",
          "issue-implementation.patch" in str(upload.get("with", {}).get("path", ""))
          and "pushed != 'true'" in str(upload.get("if", "")), upload)
    comment_run = run_text(impl)
    check("issue-bot: the issue comment explains the token scope and the fix",
          "Workflows: Read and write" in comment_run and "workflow" in comment_run, "")
    check("issue-bot: the prompt forbids scratch artifacts (no *.patch 'implementation')",
          "No `*.patch`" in (ROOT / ".hermes" / "skills" / "issue-implement" / "SKILL.md").read_text(),
          "")

    fail_step = step(impl, "Fail loudly")
    check("issue-bot: a missing implementation makes the RUN red at a named step",
          "implemented != 'true'" in str(fail_step.get("if", ""))
          and "exit 1" in fail_step.get("run", ""), fail_step.get("if"))
    # Measured on run 38517245659: the message read "the push of the # branch"
    # because this step lost the issue number.
    check("issue-bot: the fail-loud message knows WHICH issue it failed for",
          "steps.iss.outputs.issue" in str(fail_step.get("env", {}).get("ISSUE", "")), fail_step.get("env"))


def test_unit_tests_really_run():
    """The unit tests are plain scripts (pytest is not in the test image), so a
    test only counts if CI actually executes it: the validate job must reach
    the link-validator tests, every `def test_*` must be called from its file's
    main(), and every file must exit non-zero when a check fails. A test that
    is defined but never called passes CI silently."""
    import ast
    mk = (ROOT / "Makefile").read_text()

    def recipe(target):
        m = re.search(rf"\n{re.escape(target)}:\n((?:\t[^\n]*\n)+)", mk)
        return m.group(1) if m else ""
    v = run_text(load("qa-validate.yml")["jobs"]["validate"])
    for target, public in (("_validate-search", "make validate-search"),
                           ("_validate-mapped", "make validate-mapped")):
        check(f"ci: validate job runs `{public}`", public in v, "")
        check(f"ci: {target} runs the link-validator unit tests",
              "tests/test_validate_links.py" in recipe(target), recipe(target)[:200])
    # `_test` discovers its modules (issues #176/#192), so the wiring question is
    # "does the runner list it", not "is the filename in the recipe".
    check("ci: validate job runs `make test`", "make test" in v, "")
    check("ci: `make test` runs the link-validator unit tests (through the runner)",
          wired(ROOT / "tests" / "test_validate_links.py"), "")
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(f.read_text())
        defs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        main = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
        if not defs:
            continue
        check(f"ci: {f.name} has a main() runner", main is not None)
        if main is None:
            continue
        used = {n.id for n in ast.walk(main) if isinstance(n, ast.Name)}
        uncalled = [d for d in defs if d not in used]
        check(f"ci: every test_* in {f.name} is called from main()", not uncalled, uncalled)
        src = f.read_text()
        check(f"ci: {f.name} exits non-zero on failure",
              "raise SystemExit(main())" in src or "sys.exit(main())" in src, "")


def test_images_follow_their_inputs():
    """Issues #135 and #141: a merged Dockerfile/Dockerfile.test change must not
    stay inert until Sunday, the test image is published like the base image,
    and ONE path prepares the images for every job."""
    rb = (WF / "refresh-bot.yml").read_text()
    decide = rb.split("- name: Decide whether to rebuild the images", 1)[1].split("\n      - name:", 1)[0]
    tags = (ROOT / "scripts" / "ensure_image.py").read_text()

    # Given ONE definition of "built from this revision" (the tags the publisher
    # and the consumers both read)
    # Then  the decision takes the tags from that script, never inline hashing
    # The decision DELEGATES (issue #208): the step runs the one tested target, and
    # the rule itself is driven branch by branch in tests/test_ensure_image.py.
    check("images: the tags come from scripts/ensure_image.py",
          "ensure_image.py" in tags and "sha256" in tags
          and 'eval "$(python3 scripts/ensure_image.py tags)"' not in decide
          and "make rebuild-decision" in decide, decide[:200])
    check("images: the definition covers base AND test inputs",
          'BASE_FILES = ("Dockerfile", "Dockerfile.test")' in tags
          and 'TEST_FILES = ("Dockerfile.test", "requirements-test.txt")' in tags
          and "base={base_hash()}" in tags, tags[:200])
    # Then  an unpublished tag forces a rebuild of that image
    check("refresh-bot: an unpublished base tag rebuilds the base",
          "make rebuild-decision" in decide
          and "steps.decide.outputs.built == 'yes'" in rb, decide)
    check("refresh-bot: an unpublished test tag rebuilds the test image",
          "make rebuild-decision" in decide
          and "needs.build.outputs.test_built == 'yes'" in rb, decide)
    # Then  each build publishes the tag naming those inputs
    check("refresh-bot: the base build publishes its tag",
          "${{ steps.decide.outputs.base_tag }}" in rb, "")
    check("refresh-bot: the test build publishes its tag",
          "${{ needs.build.outputs.test_tag }}" in rb
          and "file: Dockerfile.test" in rb, "")
    # Then  the owner can republish both images without waiting for Sunday
    # The force value is handed to the decision (which parses it STRICTLY: FORCE=0
    # is OFF — see tests/test_ensure_image.py::test_force_is_parsed_strictly_so_zero_means_off).
    check("refresh-bot: `force_rebuild` reaches the decision",
          'FORCE="${{ inputs.force_rebuild }}"' in decide
          and "[ \"$FORCE\" = \"true\" ]" not in decide, decide)
    check("refresh-bot: the dispatch input exists",
          "force_rebuild:" in rb and "type: boolean" in rb, "")

    # Given every job that needs the images
    # Then  ONE make target prepares them (no inline pull/build left)
    mk = (ROOT / "Makefile").read_text()
    check("make: `image-ensure` exists and calls the script",
          "image-ensure:\n\tpython3 scripts/ensure_image.py ensure" in mk, "")
    check("make: `image-ensure-base` exists for image-only jobs",
          "image-ensure-base:\n\tpython3 scripts/ensure_image.py ensure-base" in mk, "")
    for name in ("qa-validate.yml", "fix-bot.yml", "issue-bot.yml"):
        text = (WF / name).read_text()
        check(f"{name}: prepares the images through `make image-ensure`",
              text.count("make image-ensure") >= 1 and "docker build -f Dockerfile.test" not in text,
              text.count("make image-ensure"))
    # Only the search jobs run the base image alone; the aggregate job runs
    # test-image targets too (`make data-gaps`, `make test`) and prepares both
    # (issue #145).
    check("refresh-bot: the search jobs use `make image-ensure-base`",
          rb.count("run: make image-ensure-base") == 1, rb.count("run: make image-ensure-base"))
    check("no workflow pulls or tags the image inline any more",
          not any("docker pull ghcr.io" in (WF / n).read_text() or "docker tag" in (WF / n).read_text()
                  for n in ("qa-validate.yml", "fix-bot.yml", "issue-bot.yml", "refresh-bot.yml")), "")
    check("dockerfile.test: its FROM is a build arg",
          "FROM ${BASE_IMAGE}" in (ROOT / "Dockerfile.test").read_text(), "")

    # Then  the guard may not report PASSED while its plugin assertion degraded
    guard = (ROOT / "scripts" / "nerve_key_check.py").read_text()
    check("nerve guard: a missing plugin is a finding, never a SKIP note",
          "SKIP:" not in guard and "may not degrade to a note" in guard, "")


def test_every_job_prepares_the_images_it_uses():
    """Issue #145: a job ran a TEST_RUN target while preparing only the BASE
    image, so `make data-gaps` died with "Unable to find image
    'trending-local-llms-test:latest'" (run 38542951338, job aggregate). The
    images a job runs are derived from the Makefile, not from memory."""
    mk = (ROOT / "Makefile").read_text()
    lines = mk.splitlines()

    # Given the public targets whose recipe executes in the TEST image
    test_targets = set()
    for i, line in enumerate(lines):
        m = re.match(r"^([a-z0-9][a-z0-9_-]*):$", line)
        if not m:
            continue
        j = i + 1
        while j < len(lines) and (lines[j].startswith("\t") or not lines[j].strip()):
            if "$(TEST_RUN)" in lines[j]:
                test_targets.add(m.group(1))
                break
            j += 1
    check("make: the TEST_RUN targets are discoverable",
          {"data-gaps", "test"} <= test_targets, sorted(test_targets))

    # When  each workflow job is read
    problems = []
    for wf in sorted(WF.glob("*.yml")):
        doc = yaml.safe_load(wf.read_text()) or {}
        for job, body in (doc.get("jobs") or {}).items():
            if not isinstance(body, dict):
                continue
            runs = [s.get("run", "") for s in (body.get("steps") or []) if isinstance(s, dict)]
            used = {t for r in runs for t in test_targets
                    if re.search(rf"(?m)(^|\s)make\s+{re.escape(t)}\b", r)}
            if not used:
                continue
            prep = "\n".join(runs)

            # Then  the job prepares that image — `make image-ensure` (both) or
            # `make image-ensure-test`. NOT `image-ensure-base`, which only looks
            # like it matches (this is the mistake the guard exists for).
            if not re.search(r"make image-ensure(?![-a-z])", prep) \
                    and not re.search(r"make image-ensure-test\b", prep):
                problems.append(f"{wf.name}:{job} runs {sorted(used)} without preparing the test image")
    check("ci: every job prepares the test image it uses", not problems, problems)

    # …and the refresh aggregate job (the measured failure) prepares both
    rb = (WF / "refresh-bot.yml").read_text()
    aggregate = rb.split("\n  aggregate:", 1)[1]
    check("refresh-bot: aggregate prepares both images",
          "run: make image-ensure\n" in aggregate, aggregate[:200])
    check("refresh-bot: its data-gap step is the TEST_RUN one it needs",
          "make data-gaps" in aggregate, "")


def test_qa_validate_runs_the_openspec_gate():
    """A PR runs the OpenSpec gate, so a spec-less or stale change cannot merge.

    Issue #172: every change is a TRACKED change — its capability spec validates,
    every `tasks.md` box is ticked and the root OPENSPEC.md index is current.
    Without this step the whole mechanism is advisory prose.
    """
    wf = load("qa-validate.yml")
    validate = wf["jobs"]["validate"]

    # Given the PR pipeline's validate job
    # When  its steps are read
    # Then  one of them runs the whole OpenSpec gate
    check("qa-validate: the validate job runs `make openspec-check`",
          "make openspec-check" in run_text(validate), run_text(validate)[:400])


def test_secret_output_guard_wired_into_qa_validate():
    """A PR runs the no-secret-VALUE guard, wired so a regression cannot merge.

    Issue #219: `make secret-scan` (gitleaks) only catches a committed
    credential VALUE. This guard catches the run-time leak shapes llgenie's
    #283 guards — a printed value, a `-e KEY=$KEY`, a `${{ secrets.X }}` in a
    `run:` block, an xtrace, an env dump, a committed credential-shaped literal.
    A guard the PR pipeline does not run is advisory prose (rule 6d).
    """
    wf = load("qa-validate.yml")
    validate = wf["jobs"]["validate"]
    v = run_text(validate)

    # Given the PR pipeline's validate job and the Makefile's gates
    # When  they are read
    # Then  the value-leak guard runs on every PR, beside the committed-value scan
    check("qa-validate: the validate job runs `make check-secret-output`",
          "make check-secret-output" in v, v[:400])
    check("qa-validate: the value guard runs in the same job as the committed-value scan",
          "make secret-scan" in v and "make check-secret-output" in v, v[:400])

    mk = (ROOT / "Makefile").read_text()
    check("make: `check-secret-output` and `secret-output-report` targets exist",
          "check-secret-output:" in mk and "secret-output-report:" in mk, "")
    check("make: the guard script is a `make` target (rule 6d)",
          "check_secret_output.py check" in mk, "")
    check("make: the guard's test is wired into `make test`'s `_test` chain",
          wired(ROOT / "tests" / "test_secret_output.py"), "")

    # And the guard genuinely passes on THIS repo (a rule the repo violates is not a rule)
    import subprocess, sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts/check_secret_output.py"), "check"],
                       capture_output=True, text=True)
    check("guard: passes on this repository", r.returncode == 0, (r.stdout + r.stderr)[:400])


def test_implement_prompt_requires_openspec_and_findings():
    """The implementer prompt demands the tracked change and the findings analysis.

    Issue #172: an implementation run must (a) create the OpenSpec change BEFORE
    the code, tick its tasks, refresh the root index and pass the gate, and
    (b) record what it noticed in `findings.md` — filed as its own issues, never
    fixed inside the change. The prompt is the only place that binds the agent.
    """
    mk = (ROOT / "Makefile").read_text()
    recipe = re.search(r"\n_implement-issue:\n((?:\t[^\n]*\n)+)", mk)
    prompt = recipe.group(1) if recipe else ""
    # Issue #549: the RULES are the implementer's project skill now — the recipe is a pointer plus
    # that run's parameters. The contract is asserted where it lives, at the same strength.
    skill = (ROOT / ".hermes" / "skills" / "issue-implement" / "SKILL.md").read_text()

    # Given the implementer's contract (its skill) and the recipe that preloads it
    # When  both are read
    # Then  the OpenSpec-first rules and the findings rules are all in the skill
    check("skill: requires the tracked change before the code",
          "make openspec-new" in skill and "before any code" in skill.lower(), skill[:400])
    check("skill: requires the tasks checklist and the gate",
          "tasks.md" in skill and "make openspec-check" in skill, skill[:400])
    check("skill: requires the root index refresh",
          "make openspec-index" in skill, skill[:400])
    check("skill: requires findings.md and its check",
          "findings.md" in skill and "make findings-check" in skill, skill[:400])
    check("skill: forbids fixing a finding inside the change",
          "never fix a finding here" in skill.lower() or "Never fix a finding" in skill, skill[:400])
    check("prompt: the recipe preloads that skill and the unattended contract",
          "-s issue-implement,bot-unattended" in prompt, prompt[-200:])
    # And the prompt is still ONE shell command (the alias must stay on the
    # continued line, or hermes auto-routes to whatever provider key is in env).
    # The flag set is one variable (issue #351): `--yolo` alone is not enough,
    # `--accept-hooks` is a separate flag, and a `-z` run that needs input detaches.
    check("prompt: the recipe keeps the `-z` line and the model flags on one command",
          prompt.count('-z "') == 1 and "-m $(HERMES_ALIAS)" in prompt
          and "$(HERMES_NONINTERACTIVE)" in prompt,
          prompt[-200:])


def test_issue_bot_files_findings_only_when_green():
    """The bot files the findings — and only after its loop went green.

    Issue #172: a red run files nothing (the work is not landed, so its analysis
    is not a verdict yet), a re-run cannot duplicate (the filing is idempotent),
    and an implementation run DEMANDS the analysis file, so "green" cannot mean
    "implemented and forgot to analyse".
    """
    wf = load("issue-bot.yml")
    impl = wf["jobs"]["implement"]
    findings_step = step(impl, "File the gaps the implementation surfaced")

    # Given the implementer job
    # When  the findings step and its gates are read
    # Then  it files with the issue/PR context, only on a green loop, with the default token
    check("findings: the bot files them through make", "make file-findings" in findings_step.get("run", ""),
          findings_step)
    check("findings: the analysis is checked first (a missing one fails loudly)",
          "make findings-check" in findings_step.get("run", ""), findings_step)
    check("findings: filing is gated on the GREEN fix loop",
          "steps.loop.outputs.green == 'true'" in str(findings_step.get("if", "")),
          findings_step.get("if"))
    check("findings: it passes the issue and PR numbers",
          findings_step.get("env", {}).get("ISSUE") == "${{ steps.iss.outputs.issue }}"
          and "steps.pr.outputs.pr_url" in str(findings_step.get("env", {}).get("PR_URL", "")),
          findings_step.get("env"))
    check("findings: it files with the default token (issues: write)",
          findings_step.get("env", {}).get("GH_TOKEN") == "${{ github.token }}", findings_step.get("env"))
    check("findings: an implementation run demands the analysis (REQUIRE_FINDINGS)",
          str(impl.get("env", {}).get("REQUIRE_FINDINGS")) == "1", impl.get("env"))
    # A gap that cannot become an issue must be LOUD: the step may not swallow a
    # failure (no continue-on-error, no `|| true`), or a run would report the work
    # as done while the finding evaporated as prose (the defect rule 6e names).
    check("findings: the filing step is not allowed to fail silently",
          findings_step.get("continue-on-error") in (None, False)
          and "|| true" not in findings_step.get("run", ""), findings_step)
    # And the CLI image `make openspec-check` runs in is published like the others.
    refresh = load("refresh-bot.yml")
    ospec = refresh["jobs"].get("openspec-image", {})
    check("openspec image: refresh-bot publishes it on the same hash-tag rule",
          "make openspec-check" in (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
          and "OPENSPEC_IMAGE" in str(refresh.get("env", {})), refresh.get("env"))
    check("openspec image: the build uses openspec/Dockerfile and pushes the hash tag",
          str(ospec.get("steps", "")) .find("openspec/Dockerfile") >= 0
          and "decide.outputs.openspec_tag" in str(ospec.get("steps", "")), ospec.get("steps"))
    check("openspec image: its decision is the same one tested unit (issue #208)",
          "make rebuild-decision" in str(ospec.get("steps", ""))
          and "decide.outputs.publish_openspec == 'no'" in str(ospec.get("steps", "")),
          ospec.get("steps"))


def test_issue_bot_announces_its_window():
    """The implementer posts the start comment the reviewer defers to (#179)."""

    # Given the implementer pipeline and its steps, in order
    wf = load("issue-bot.yml")
    impl = wf["jobs"]["implement"]
    names = [s.get("name", "") for s in steps(impl)]
    announce = next((s for s in steps(impl) if "Announce the window" in s.get("name", "")), {})
    announce_at = next((i for i, n in enumerate(names) if "Announce the window" in n), None)
    implement_at = next((i for i, n in enumerate(names) if n.startswith("Implement the issue")), None)

    # Then  it exists, is posted BEFORE the implementation, and carries the marker
    check("issue-bot: a start comment announces the implementer window", bool(announce), names)
    check("issue-bot: the window opens BEFORE the body is implemented",
          announce_at is not None and implement_at is not None and announce_at < implement_at,
          f"announce={announce_at} implement={implement_at}")
    body = announce.get("run", "")
    check("issue-bot: the marker is the one the reviewer reads",
          "<!-- issue-bot-start:" in body, body[:200])
    check("issue-bot: the start comment names the branch and the run",
          "BRANCH" in body and "GITHUB_RUN_ID" in body, body[:200])
    # Comments need `issues: write` on the DEFAULT token: the owner PAT is scoped
    # to Actions/Contents/Pull-requests and cannot comment (#124, measured).
    check("issue-bot: the announcement uses the default token, not the PAT",
          announce.get("env", {}).get("GH_TOKEN") == "${{ github.token }}", announce.get("env"))
    # Both entry paths (an opened issue and the hourly sweep) announce a window.
    check("issue-bot: the announcement is not gated to one trigger path",
          announce.get("if") == "steps.iss.outputs.implement == 'true'", announce.get("if"))
    # The window must not be announced before the issue resolved, and must be a
    # working file rather than a commit: the scratch reset names it.
    check("issue-bot: the start comment file can never be committed",
          "start.md" in (ROOT / ".gitignore").read_text(), "")


def test_the_queue_rule_has_one_implementation():
    """Both bots read `make issue-queue`; neither pastes the rule again (#179)."""

    # Given the two pipelines and the Makefile
    bot = load("issue-bot.yml")
    review = load("issue-review-bot.yml")
    makefile = (ROOT / "Makefile").read_text()
    pick_run = run_text(bot["jobs"]["pick"])

    # Then  the implementer picks through the shared target
    check("queue: issue-bot's pick runs `make issue-pick` (the producer's own line)",
          "make issue-pick" in pick_run, pick_run[:400])
    check("queue: issue-bot's pick no longer pastes the branch/PR rule inline",
          "matching-refs" not in pick_run and "gh pr list" not in pick_run, pick_run[:400])
    check("queue: the reviewer picks through the shared target",
          "make review-issue-pick" in run_text(review["jobs"]["pick"]), "")
    check("queue: the pick job checks out the repo it runs its own target from",
          any("actions/checkout" in str(s.get("uses", "")) for s in steps(bot["jobs"]["pick"])), "")
    check("queue: the gap is ONE variable in the Makefile",
          "REVIEW_GAP_HOURS := 3" in makefile, "")


def test_issue_review_bot():
    """The reviewer's wiring (issue #179): one issue, two paths, no code, no merge."""

    # Given the reviewer pipeline
    wf = load("issue-review-bot.yml")
    triggers = wf["on"]
    guard = wf["jobs"]["guard"]
    pick = wf["jobs"]["pick"]
    review = wf["jobs"]["review"]
    all_run = "\n".join(run_text(j) for j in wf["jobs"].values())

    # Then  it reacts to the hourly cron and an owner dispatch ONLY — a review
    # must not fire on every issue event (an edit or a comment is not a review).
    check("review: trigger surface is schedule + workflow_dispatch only",
          set(triggers) == {"schedule", "workflow_dispatch"}, list(triggers))
    crons = [c["cron"] for c in triggers["schedule"]]
    check("review: hourly and OFF the hour (GitHub drops on-the-hour crons)",
          crons == ["41 * * * *"], crons)
    check("review: the offset is not the implementer's sweep",
          "19 * * * *" not in crons, crons)
    check("review: a re-run is owner-gated before any secret",
          "guard" in review.get("needs", []) and bool(steps(guard)), review.get("needs"))
    check("review: the guard refuses anyone but the owner / a write collaborator",
          "collaborators/$u/permission" in run_text(guard), "")

    # The picker decides the run: one issue, and every candidate inside a window
    # is a green no-op instead of a body rewrite.
    check("review: the review job is skipped when nothing is reviewable",
          "needs.pick.outputs.action != 'none'" in str(review.get("if", "")), review.get("if"))
    check("review: one reviewer per issue (per-issue concurrency)",
          "issue-review-issue-" in str(review.get("concurrency", {}).get("group", "")),
          review.get("concurrency"))
    check("review: runs only when the picked issue is not empty",
          "needs.pick.outputs.issue != ''" in str(review.get("if", "")), review.get("if"))

    # The window is re-checked BEFORE anything is written (the implementer may
    # have started while the run prepared), and the body's rewrite is verified.
    check("review: the TOCTOU guard re-checks the window before writing",
          "review-issue-guard ISSUE=\"$ISSUE\" PATH=body" in all_run, "")
    check("review: the refined body must keep every invisible marker",
          "review-issue-check-markers" in all_run, "")
    check("review: the window path PROVES the body was not edited",
          "review-issue-body-hash" in all_run and "the window path wrote issue-body.md" in all_run, "")
    check("review: one reply per window (guarded, not hoped for)",
          "review-issue-guard ISSUE=\"$ISSUE\" PATH=window" in all_run, "")
    check("review: it replies on the issue, never by editing it in the window path",
          "gh issue edit" not in str(step(review, "Reply once").get("run", "")), "")
    check("review: the window reply carries the marker the next run reads",
          "<!-- issue-review: window" in all_run and "GITHUB_RUN_ID" in all_run, "")

    # Analysis ships issues: the filing is the implementer's OWN path (dedup,
    # label verification, origin link) and is never allowed to fail silently.
    findings = step(review, "File the gaps")
    check("review: findings are filed through the shared filing path",
          "make findings-check" in findings.get("run", "") and "make file-findings" in findings.get("run", ""),
          findings.get("run", "")[:200])
    check("review: a filing failure is loud (no continue-on-error, no `|| true`)",
          findings.get("continue-on-error") in (None, False) and "|| true" not in findings.get("run", ""), findings)

    # The reviewer refines issues; it never ships code — no push, no branch, no
    # merge, and no write permission beyond issues.
    check("review: no push, branch or merge anywhere",
          all(k not in all_run for k in ("git push", "git checkout -b", "gh pr create",
                                         "gh pr merge", "--admin")), "")
    check("review: permissions are issues: write + contents: read only",
          wf["permissions"] == {"contents": "read", "issues": "write"}, wf["permissions"])
    check("review: the owner PAT is never used (it cannot comment, #124)",
          PAT not in all_run and "secrets.FIXBOT_DISPATCH_TOKEN" not in str(wf), "")

    # Every repo-logic command is a make target; only gh/git orchestration is inline.
    check("review: no raw script invocation in the workflow",
          "python3 scripts/" not in all_run and "scripts/issue_" not in all_run, "")
    check("review: the reviewer's own steps go through make",
          all(target in all_run for target in ("make review-issue-pick", "make review-issue-mark",
                                               "make review-issue-finish", "make review-issue")), "")

    # Issue #344: the pick's diagnostics never become ISSUE. Issue #548: the step takes
    # each value WHOLE and refuses one carrying whitespace (the producer refuses it too),
    # and the resolve step names the defect instead of turning it into a 404.
    pick_run = run_text(pick)
    check("review: the pick takes each value WHOLE — a whitespace split is what truncated it",
          "awk '{print $1}'" not in pick_run and "*[[:space:]]*" in pick_run, pick_run[:600])
    check("review: the pick refuses a non-numeric issue= loudly",
          "*[!0-9]*" in pick_run and "not an issue number" in pick_run, pick_run[:600])
    resolve_run = str(step(review, "Resolve the issue").get("run", ""))
    check("review: the resolve step refuses a non-numeric ISSUE before any gh read",
          "*[!0-9]*" in resolve_run and "not an issue number" in resolve_run
          and resolve_run.index("not an issue number") < resolve_run.index("gh api"), resolve_run[:400])

    # A failing thread step stops the steps that consume its value, and the window
    # close is gated on the window THIS run opened: one broken value, one failure.
    thread = step(review, "Write the issue and its comments")
    check("review: the thread step has an id its consumers can gate on",
          thread.get("id") == "thread", thread.get("id"))
    for name in ("Open the reviewer window", "Route (re-check", "Refine the issue",
                 "Every invisible marker", "Publish the refined body",
                 "Review as a reply", "Prove the window path", "Reply once",
                 "File the gaps"):
        consumed = step(review, name)
        check(f"review: `{name}` is gated on the thread step",
              "steps.thread.outcome == 'success'" in str(consumed.get("if", "")),
              consumed.get("if"))
    close_if = str(step(review, "Close the reviewer window").get("if", ""))
    check("review: the window close is gated on the mark (only a window we opened)",
          "always()" in close_if and "steps.mark.outcome == 'success'" in close_if, close_if)

    # A run that produced nothing to read is a defect, not a green no-op.
    loud = step(review, "Fail loudly")
    check("review: a silent review is a loud failure",
          "produced no comment.md" in loud.get("run", "") and loud.get("continue-on-error") in (None, False), loud)
    check("review: the reviewer window is closed even when a step failed",
          "always()" in str(step(review, "Close the reviewer window").get("if", "")), "")


def test_the_reviewer_never_edits_an_issue_inside_a_window():
    """The two paths are wired to the exact way they touch an issue (#179)."""

    # Given the reviewer pipeline and the two prompt recipes it calls
    wf = load("issue-review-bot.yml")
    review = wf["jobs"]["review"]
    makefile = (ROOT / "Makefile").read_text()
    all_run = "\n".join(run_text(j) for j in wf["jobs"].values())

    # Then  the body path publishes only through the guarded route, and the
    # window path has no body write at all.
    publish = step(review, "Publish the refined body")
    check("paths: the body is published only on the `body` route",
          publish.get("if") == f"{THREAD_GATE} && steps.route.outputs.path == 'body'",
          publish.get("if"))
    refine = step(review, "Refine the issue")
    check("paths: the refinement runs only on the `body` route",
          refine.get("if") == f"{THREAD_GATE} && steps.route.outputs.path == 'body'", refine.get("if"))
    reply = step(review, "Review as a reply")
    check("paths: the reply runs only on the `window` route",
          reply.get("if") == f"{THREAD_GATE} && steps.route.outputs.path == 'window'", reply.get("if"))

    # The two prompts state the hard rule of their path. Issue #549: the RULES live in the
    # reviewer's project skill (the recipes are pointers that preload it), so they are asserted
    # where they live — at the same strength — and the recipes are asserted to preload it.
    body_prompt = makefile.split("_review-issue:")[1].split(".PHONY: review-issue")[0]
    window_prompt = makefile.split("_review-issue-window:")[1].split(".PHONY: review-issue-window")[0]
    review_skill = (ROOT / ".hermes" / "skills" / "issue-review" / "SKILL.md").read_text()
    check("skill: it must never implement the issue",
          "Never implement" in review_skill, review_skill[:200])
    check("skill: the markers are byte-identical or the run is wrong",
          "byte-identical" in review_skill, "")
    check("skill(window): the body is declared off-limits",
          "off-limits" in review_skill.lower() and "issue-body.md" in review_skill, "")
    check("skill(window): the reply is bounded and must carry evidence",
          "at most 5 bullets" in review_skill and "evidence" in review_skill, "")
    check("skill: the container has no gh, so it forbids running it",
          "no `gh`" in review_skill.lower(), "")
    check("skill: both paths ship their findings as issues",
          "findings.md" in review_skill, "")
    check("prompt(body): the recipe preloads the reviewer's skill",
          "-s issue-review,bot-unattended" in body_prompt, body_prompt[:200])
    check("prompt(window): the recipe preloads the reviewer's skill",
          "-s issue-review,bot-unattended" in window_prompt, window_prompt[:200])
    check("prompt(window): the recipe names its own path",
          "WINDOW path" in window_prompt, window_prompt[:200])
    check("review: the refinement clears `needs-refinement` from the workflow, not the agent",
          "remove-label needs-refinement" in all_run, "")


def test_no_pipeline_opens_a_draft_pr() -> None:
    """Issue #276 / AGENTS.md rule 6e: a run opens a REVIEWABLE PR, never a draft.

    `auto-merge` requires `github.event.pull_request.draft == false`, so a draft is valid,
    green and permanently unmergeable — the run reports success while the only mechanism
    that could land the change is disabled by a flag. The merge side is asserted
    (`auto-merge: never a draft PR`); this is the other half: nothing may OPEN one.
    """
    print("\nissue #276 — a pipeline opens a reviewable PR, never a draft")
    offenders = []
    for path in sorted(WF.glob("*.yml")):
        for run in re.findall(r"gh pr create[^\n]*", path.read_text(encoding="utf-8")):
            if "--draft" in run:
                offenders.append(f"{path.name}: {run.strip()[:80]}")
    check("no `gh pr create` anywhere passes --draft", not offenders, offenders)

    agg = step(load("refresh-bot.yml")["jobs"]["aggregate"], "Commit + open PR if changed")
    check("refresh-bot: its data PR is created ready for review",
          "gh pr create" in agg.get("run", "") and "--draft" not in agg.get("run", ""), agg.get("run", "")[:120])
    impl = load("issue-bot.yml")["jobs"]["implement"]
    pr = step(impl, "Open the PR")
    check("issue-bot: its implementation PR is created ready for review",
          "gh pr create" in pr.get("run", "") and "--draft" not in pr.get("run", ""), pr.get("run", "")[:120])
    cond = str(load("qa-validate.yml")["jobs"]["auto-merge"].get("if", ""))
    check("qa-validate: the merge gate still refuses a draft (the reason for the rule)",
          "draft == false" in cond, cond)


def test_the_fail_loudly_step_asks_whether_the_issue_still_needs_doing():
    """Issue #520: a run whose issue was closed mid-flight is a finished outcome, not a failure.

    Measured on run 39612330011: #183 picked at 14:37, PR #517 merged and closed it at 14:38, and
    the run ended RED at 14:41 over work that had been done. The step must ask the ONE seam
    (`make issue-state`) FIRST, treat 4 (closed) as GREEN with a comment on the thread, and leave
    every other outcome exactly as red as it was.
    """
    # Given the implementer pipeline's final failure step
    wf = load("issue-bot.yml")
    failing = step(wf["jobs"]["implement"], "Fail loudly when the implementation did not happen")
    body = failing.get("run", "")

    # Then  the state read comes first, and cannot abort the step before it branches
    check("issue-bot: the failure step asks the issue's state FIRST (issue #520)",
          "make issue-state" in body
          and body.index("make issue-state") < body.index('SCOPE_ERROR:-'),
          body[:200])
    check("issue-bot: the state read runs under `set +e` so the step can branch on it",
          "set +e" in body and "STATE_RC=$?" in body, "")

    # And  a CLOSED issue ends the run GREEN, with ONE marker-deduplicated comment
    check("issue-bot: a CLOSED issue (exit 4) ends the run GREEN",
          'if [ "$STATE_RC" = "4" ]' in body, body[:300])
    closed_branch = body.split('if [ "$STATE_RC" = "4" ]')[1].split("\n          fi")[0]
    check("issue-bot: …and says so on the issue thread with the default token",
          "gh issue comment" in closed_branch and "issue-bot-already-fixed" in closed_branch
          and str(failing.get("env", {}).get("GH_TOKEN")) == "${{ github.token }}",
          failing.get("env"))
    check("issue-bot: an unreadable state (exit 2) is NOT excused as closed", '= "2"' not in closed_branch,
          closed_branch[:200])

    # And  the red paths are untouched: a still-open issue with no work, and the token scope
    check("issue-bot: a still-open issue keeps BOTH red paths",
          "produced no implementation" in body and "SCOPE_ERROR" in body
          and body.rstrip().endswith("exit 1"), body[-160:])


def test_issue_bot_asserts_the_base_it_cuts_from() -> None:
    """Issue #271 / AGENTS.md rule 6n: a branch is cut from the FETCHED base, asserted.

    The old resume path was `git checkout "$BRANCH"` in a clone holding ONE ref
    (`actions/checkout` + `ref: master`), so it died with `pathspec ... did not match any
    file(s) known to git` — and the marker-word assertion on it stayed green. The base a
    fresh runner clone starts from is only `origin/master` by accident, so it is asserted
    before anything is implemented, and both branch paths go through the one Makefile seam.
    """
    print("\nissue #271 — the base is fetched and asserted before a branch is cut")
    ib = load("issue-bot.yml")
    impl = ib["jobs"]["implement"]
    impl_steps = steps(impl)
    names = [str(st.get("name", "")) for st in impl_steps]
    base = next((st for st in impl_steps if "make base-check" in str(st.get("run", ""))), None)
    check("issue-bot: asserts the base it cuts from (make base-check)", base is not None, names)
    check("issue-bot: the assertion is a step of the implement job, run only when implementing",
          base is not None and "implement == 'true'" in str(base.get("if", "")), base and base.get("if"))
    check("issue-bot: it runs BEFORE anything is implemented",
          base is not None
          and names.index(str(base.get("name"))) < names.index("Implement the issue (Hermes, through make)"),
          names)
    body = run_text(impl)
    check("issue-bot: the branch is adopted at commit time, never a bare checkout (issue #500)",
          "make branch-adopt" in body and "git switch -c" not in body, "")
    check("issue-bot: the commit is rebased onto the fetched tip before the push (issue #500)",
          0 <= body.find("make base-rebase") < body.find("git push"), "")
    rb = load("refresh-bot.yml")
    # `aggregate` cuts `ci/trending-refresh-<UTC>` after ~40 min of searching, so its
    # checkout is behind by construction and the STRICT refusal would discard the run
    # (issue #448, measured: run 39329834698, 4/4 legs green, nothing merged). It must
    # ADVANCE onto the fetched base instead — and must NOT carry `base-check`, which
    # would fail the job again the moment master moves.
    agg = [st for st in steps(rb["jobs"]["aggregate"]) if "make base-advance" in str(st.get("run", ""))]
    check("refresh-bot: the job that cuts ci/trending-refresh-* advances onto the fetched base",
          bool(agg) and "origin/master" in str(agg[0].get("name", "")), "")
    check("refresh-bot: the aggregate does NOT run the strict base-check (it has written nothing yet)",
          not [st for st in steps(rb["jobs"]["aggregate"]) if "make base-check" in str(st.get("run", ""))],
          [st.get("name") for st in steps(rb["jobs"]["aggregate"])])


#: Steps whose `run` WRITES an issue — creates one, or labels / comments on one.
#: AGENTS.md §6b states the rule for exactly this class of write: "issue reads and
#: comments use the default `github.token` with `permissions: issues: write` (the
#: PAT has no Issues scope)". Measured twice now: the PAT was refused a comment
#: (#124) and the data-gap filing lost its label while `gh` returned 0 (#277).
_ISSUE_WRITE = re.compile(
    r"gh\s+issue\s+(?:create|edit|comment|close|reopen)"
    r"|make\s+(?:data-gap-issue|file-findings|issue-skip-note|issue-verdict|code-review-file|queued-alarm)\b")


def _job_can_write_issues(wf: dict, job: dict) -> bool:
    """`issues: write` for the token a step of this job uses.

    A JOB-level `permissions:` block REPLACES the workflow-level one, so the job's
    own block is the answer when it has one.
    """
    job_perm = job.get("permissions")
    if isinstance(job_perm, str):
        return job_perm == "write-all"
    if isinstance(job_perm, dict):
        return str(job_perm.get("issues", "")).lower() == "write"
    wf_perm = wf.get("permissions")
    if isinstance(wf_perm, str):
        return wf_perm == "write-all"
    if isinstance(wf_perm, dict):
        return str(wf_perm.get("issues", "")).lower() == "write"
    return True  # absent `permissions:` means the default token's default scopes


def test_issue_writes_use_the_default_token():
    """Issue #277: an issue write made with the owner PAT is refused or silently
    dropped — the PAT declares Actions/Contents/Pull-requests/Workflows and NO
    Issues scope. The measured failure is not a 403: `gh issue create --label
    data-gap-analysis` returned 0 having applied NO label, `gh issue edit
    --add-label` then could not repair it, the step was `continue-on-error`, and
    BOTH bot queues stayed empty (`make issue-queue` -> `candidates=0`,
    `make review-issue-pick` -> `action=none`) while every run reported green.
    This is the class rule, not the site: EVERY step that writes an issue must use
    the token that can write one.
    """
    problems: list[str] = []
    checked = 0
    for f in sorted(WF.glob("*.yml")):
        wf = load(f.name)
        for job_name, job in (wf.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for st in steps(job):
                run = str(st.get("run", "") or "")
                if not _ISSUE_WRITE.search(run):
                    continue
                checked += 1
                token = str((st.get("env") or {}).get("GH_TOKEN", ""))
                where = f"{f.name}:{job_name}:{st.get('name')}"
                if "github.token" not in token:
                    problems.append(f"{where} writes an issue without the default token ({token or 'no GH_TOKEN'})")
                elif not _job_can_write_issues(wf, job):
                    problems.append(f"{where} writes an issue but its job does not declare `issues: write`")
    check("ci: issue-writing steps are discovered (the guard is not vacuous)", checked >= 5, checked)
    check("ci: every issue write uses the token that can write issues", not problems, problems)

    # …and the measured case, named so the fix cannot be reverted quietly
    agg = load("refresh-bot.yml")["jobs"]["aggregate"]
    filer = next((s for s in steps(agg) if "make data-gap-issue" in str(s.get("run", ""))), {})
    check("refresh-bot: the data-gap filer uses the default token",
          "github.token" in str((filer.get("env") or {}).get("GH_TOKEN", "")), filer.get("env"))
    check("refresh-bot: the aggregate job asks for `issues: write`",
          str((agg.get("permissions") or {}).get("issues", "")).lower() == "write", agg.get("permissions"))


#: Any step that calls a repo target. `make <target>` only exists where the
#: Makefile is, and the Makefile only exists where the job checked the repo out.
_MAKE_CALL = re.compile(r"(?m)(?:^|\s)make\s+[a-z][a-z0-9-]*")


def test_a_step_that_calls_make_runs_after_the_checkout():
    """Issue #281: issue-bot's `implement` job ran `make issue-thread` in step 2,
    before `actions/checkout` in step 3 — so the sweep died with

        make: *** No rule to make target 'issue-thread'.  Stop.

    and steps 3-18 (checkout, base-check, images, smoke, announce, implement, push,
    PR, fix loop) were ALL skipped: the implementer could not implement anything
    while every other bot kept running. A bare runner has no Makefile, so this is
    the invariant: a `make` call needs the checkout to have happened first.
    """
    problems: list[str] = []
    checked = 0
    for f in sorted(WF.glob("*.yml")):
        wf = load(f.name)
        for job_name, job in (wf.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            job_steps = steps(job)
            checkout_at = next((i for i, s in enumerate(job_steps)
                                if str(s.get("uses", "")).startswith("actions/checkout")), None)
            for i, s in enumerate(job_steps):
                if not _MAKE_CALL.search(str(s.get("run", "") or "")):
                    continue
                checked += 1
                where = f"{f.name}:{job_name}:{s.get('name')}"
                if checkout_at is None:
                    problems.append(f"{where} calls make in a job that never checks the repo out")
                elif i < checkout_at:
                    problems.append(f"{where} calls make at step {i + 1}, BEFORE the checkout at {checkout_at + 1}")
    check("ci: make-calling steps are discovered (the guard is not vacuous)", checked >= 10, checked)
    check("ci: every `make` call happens after its job's checkout", not problems, problems)

    # …and the measured case, named: the implementer's resolver must need NO repo,
    # while the thread it reads is rendered after the checkout.
    impl = load("issue-bot.yml")["jobs"]["implement"]
    names = [str(s.get("name", "")) for s in steps(impl)]
    resolver = next((s for s in steps(impl) if str(s.get("name", "")).startswith("Resolve the issue")), {})
    check("issue-bot: the resolver calls no repo target", not _MAKE_CALL.search(str(resolver.get("run", ""))),
          str(resolver.get("run", ""))[:200])
    thread = next((s for s in steps(impl) if "issue-thread" in str(s.get("run", ""))), None)
    check("issue-bot: the thread is rendered by a step of the implement job", thread is not None, names)
    check("issue-bot: …after the checkout",
          thread is not None
          and names.index(str(thread.get("name")))
          > names.index("Checkout master (PAT, so its push re-triggers CI)"), names)
    check("issue-bot: an empty thread is a loud failure",
          thread is not None and "test -s issue.md" in str(thread.get("run", "")), "")


#: A `gh` subcommand whose owner/repo is resolved IMPLICITLY — from the git
#: remote — and so needs either a checkout or `GH_REPO` in the environment.
#: `gh api repos/$REPO/...` carries its own path and is never matched.
_GH_IMPLICIT = re.compile(r"\bgh\s+(?:pr|issue|run|release|workflow|label|search)\b([^\n|;&]*)")


def test_gh_before_the_checkout_names_the_repo():
    """`gh` resolves owner/repo from a git remote. A job that writes to the PR
    BEFORE it checks anything out dies with `fatal: not a git repository` — and
    because the announce step is what fails, the checkout and the whole fix loop
    are SKIPPED. Measured on PR #330 (run 39027053298): the refresh PR stayed red
    on one dead Hugging Face link and nothing was there to repair it, while every
    run still reported the defect as "fix-bot was dispatched"."""
    offenders = []
    for path in sorted(WF.glob("*.yml")):
        doc = yaml.safe_load(path.read_text()) or {}
        for job_name, job in (doc.get("jobs") or {}).items():
            steps = job.get("steps") or []
            checkout = next((i for i, s in enumerate(steps)
                             if "actions/checkout" in str(s.get("uses", ""))), None)
            job_env = job.get("env") or {}
            for i, step in enumerate(steps):
                if checkout is not None and i >= checkout:
                    continue  # after the checkout, `gh` has the remote
                run = step.get("run") or ""
                for m in _GH_IMPLICIT.finditer(run):
                    if "--repo" in m.group(1) or re.search(r"\s-R\s", m.group(1)):
                        continue  # names the repo itself
                    if "GH_REPO" in job_env or "GH_REPO" in (step.get("env") or {}):
                        continue
                    offenders.append(f"{path.name}:{job_name}:{step.get('name', '?')}")
    check("gh before a checkout: no job calls gh implicitly without GH_REPO",
          not offenders, offenders)

    # The measured regression, named on its own so this guard fails on the OLD
    # file even if the scan above goes vacuous.
    fix_env = load("fix-bot.yml")["jobs"]["fix"].get("env") or {}
    check("gh before a checkout: fix-bot's PR writes name the repo (PR #330)",
          "GH_REPO" in fix_env, sorted(fix_env))



def test_the_validate_job_checks_out_the_pr_tree_not_the_merge_result():
    """Issue #432: `pull_request` checks out the MERGE COMMIT by default, so `make
    openspec-check` compared the index with a tree carrying every OTHER open change and
    reported it stale on branches whose index was current — a PR could not go green while a
    sibling merged first. The gate is about the contributor's own tree."""
    doc = load("qa-validate.yml")
    steps = doc["jobs"]["validate"]["steps"]
    checkout = next(s for s in steps if "actions/checkout" in str(s.get("uses", "")))
    ref = str((checkout.get("with") or {}).get("ref", ""))
    check("qa-validate: the validate job checks out the PR head",
          "github.event.pull_request.head.sha" in ref, ref)
    check("qa-validate: … and falls back to github.sha on a push to master",
          "github.sha" in ref, ref)
    check("qa-validate: full history is still fetched (authorship guard, #317)",
          str((checkout.get("with") or {}).get("fetch-depth")) == "0", checkout.get("with"))

#: Pipelines no PR runs at all: `schedule` / `workflow_dispatch` only, so a broken edit to one
#: is invisible to the PR that makes it — qa-validate never executes it (issue #231). Each MUST
#: name the test module that exercises its logic inside `make test`, and the map is itself
#: checked in both directions so it cannot lie or go stale.
DISPATCH_ONLY_COVERAGE = {
    "code-review-bot.yml": "tests/test_workflows.py",     # guard, issue writes, step order
    "fix-bot.yml": "tests/test_fix_loop.py",              # the loop it runs, push gating
    "issue-bot.yml": "tests/test_issue_review.py",        # the queue, the windows, the pick
    "issue-review-bot.yml": "tests/test_issue_review.py",
    "queued-alarm.yml": "tests/test_queued_run_alarm.py",  # the decision it makes
    "pr-health.yml": "tests/test_pr_health.py",  # the silent-PR decision it makes
    "publish-agent-image.yml": "tests/test_publish_agent_image.py",  # the publish decision
    "refresh-bot.yml": "tests/test_refresh_run_block.py",  # the window block it composes
    "architecture-bot.yml": "tests/test_architecture_bot.py",  # the block it regenerates, its guard
}

#: Events that mean "a pull request runs this pipeline".
PR_EXERCISE_EVENTS = ("pull_request", "pull_request_target", "push")


def workflow_triggers(doc: dict) -> set:
    """The event names a workflow declares in `on:` (PyYAML turns bare `on` into True)."""
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return {str(x) for x in on}
    if isinstance(on, dict):
        return {str(k) for k in on}
    return set()


def coverage_problems(triggers: dict, coverage: dict) -> list:
    """Every pipeline PR-exercised, or named with the test that covers it (issue #231)."""
    problems = []
    for name, events in sorted(triggers.items()):
        runs_on_pr = bool(set(events) & set(PR_EXERCISE_EVENTS))
        cov = coverage.get(name)
        if runs_on_pr and cov:
            problems.append(f"{name}: a PR already runs it "
                            f"({sorted(set(events) & set(PR_EXERCISE_EVENTS))}) — drop it from "
                            f"DISPATCH_ONLY_COVERAGE so the map cannot claim otherwise")
        elif not runs_on_pr and not cov:
            problems.append(f"{name}: runs only on {sorted(events) or ['nothing']} — no PR "
                            f"exercises it and no coverage is named (issue #231)")
        elif cov and not (ROOT / cov).is_file():
            problems.append(f"{name}: coverage module {cov} does not exist")
    return problems


def test_every_pipeline_is_exercised_on_a_pr_or_names_its_coverage():
    """A dispatch-only pipeline ships broken (issue #231): nothing on a PR runs it, so a bad
    step, a bad `needs:` or a renamed target is discovered by the first real run — with
    secrets and side effects — instead of by the PR that made it."""
    triggers = {}
    for path in sorted(WF.glob("*.yml")):
        triggers[path.name] = workflow_triggers(yaml.safe_load(path.read_text()) or {})
    problems = coverage_problems(triggers, DISPATCH_ONLY_COVERAGE)
    check("pipelines: every workflow is PR-exercised or names the test that covers it",
          not problems, problems)
    check("pipelines: the coverage map is not empty (a vacuous guard)", bool(DISPATCH_ONLY_COVERAGE),
          "")
    # A guard that cannot fail proves nothing: an unclassified dispatch-only pipeline is REFUSED.
    fake = coverage_problems({"new-bot.yml": {"workflow_dispatch"}}, {})
    check("pipelines: an unclassified dispatch-only workflow FAILS the guard", bool(fake), fake)
    # …and a stale entry (PR-triggered, yet listed as dispatch-only) is refused too.
    stale = coverage_problems({"qa-validate.yml": {"pull_request", "push"}},
                              {"qa-validate.yml": "tests/test_workflows.py"})
    check("pipelines: a stale coverage entry is refused", bool(stale), stale)
    # Every named module must be discovered by the one test runner (scripts/run_tests.sh runs
    # tests/test_*.py), so "covered" means "executed by make test".
    undiscovered = [m for m in DISPATCH_ONLY_COVERAGE.values()
                    if not (m.startswith("tests/test_") and m.endswith(".py"))]
    check("pipelines: every coverage module is one the test runner discovers",
          not undiscovered, undiscovered)



def test_the_closure_check_reruns_when_the_pr_body_is_edited():
    """Issue #290: the check's input is the PR BODY, and a body changes without a commit.
    `qa-validate` triggers on the default `pull_request` types (no `edited`), so a body that
    broke its closure kept a green check until an unrelated push."""
    doc = load("pr-closure.yml")
    triggers = doc.get("on") or doc.get(True) or {}
    types = set((triggers.get("pull_request") or {}).get("types") or [])
    check("pr-closure: it triggers on a BODY EDIT", "edited" in types, sorted(types))
    check("pr-closure: … and on the ordinary PR events",
          {"opened", "synchronize", "reopened"} <= types, sorted(types))
    steps = doc["jobs"]["closure"]["steps"]
    check("pr-closure: the closure job checks the repository out",
          any("actions/checkout" in str(s.get("uses", "")) for s in steps), [s.get("name") for s in steps])
    check("pr-closure: it runs the check through the Makefile (rule 6m)",
          any(s.get("run", "").strip() == "make pr-closure" for s in steps),
          [s.get("run") for s in steps])
    check("pr-closure: it needs the guard (rule 6j)",
          doc["jobs"]["closure"].get("needs") == "guard", doc["jobs"]["closure"].get("needs"))
    # …and the pipeline stays READ-ONLY: it never pushes, comments or merges.
    body = json.dumps(doc)
    offenders = [w for w in ("git push", "gh pr merge", "gh pr comment", "--admin") if w in body]
    check("pr-closure: read-only (no push, no comment, no merge)", not offenders, offenders)
    # qa-validate keeps its own closure gate: this pipeline ADDS a trigger, it does not move it.
    qa = load("qa-validate.yml")
    qa_steps = [s.get("run", "").strip() for s in qa["jobs"]["validate"]["steps"]]
    check("pr-closure: qa-validate still runs the closure check itself",
          "make pr-closure" in qa_steps, qa_steps[-6:])


def test_a_job_that_runs_the_suite_checks_out_the_whole_history() -> None:
    """issue #552: `make test` reads `git log`, so a shallow checkout reds it by construction.

    `actions/checkout` defaults to `fetch-depth: 1`. The refresh `aggregate` job runs the QA pass
    (`make qa-report` → `validate` + `test`) on that default, and `make test` includes
    `check-commit-authorship`, which reads `git log origin/master..HEAD` — measured on run
    40126898852: `[qa-report] make test reported findings (rc=2)`, `is-shallow-repository=true`.
    Because the aggregate treats its QA pass as advisory ("data still lands for review"), that
    permanent red made a REAL defect indistinguishable from standing noise, and the run stayed
    green. Every job that runs the suite must therefore ask for the full history.
    """
    print("\nissue #552 — a job that runs `make test` checks out the whole history")
    callers: list[str] = []
    for path in sorted(WF.glob("*.yml")):
        doc = load(path.name)
        for name, job in (doc.get("jobs") or {}).items():
            runs = [re.sub(r"(?m)^\s*#.*$", "", s.get("run") or "") for s in steps(job)]
            if not any(re.search(r"make\s+(test|qa-report|check-commit-authorship)\b", r)
                       for r in runs):
                continue
            callers.append(f"{path.name}:{name}")
            full = [s for s in steps(job)
                    if str((s.get("uses") or "")).startswith("actions/checkout")
                    and str((s.get("with") or {}).get("fetch-depth")) == "0"]
            check(f"{path.name} {name}: the checkout is the full history (fetch-depth: 0)",
                  bool(full), [s.get("uses") for s in steps(job)])
    check("the guard found the jobs that run the suite (not vacuous)", len(callers) >= 2, callers)
    refresh = load("refresh-bot.yml")["jobs"]["aggregate"]
    check("refresh-bot aggregate: it really is the QA runner",
          any("make qa-report" in (s.get("run") or "") for s in steps(refresh)), "")


def test_issue_bot_salvages_a_detached_runs_work() -> None:
    """issue #554: rc=3 AFTER implementing must not throw the change away.

    The unattended contract is preloaded, but a model can still call `clarify` once — measured on
    run 40168796244, ~30 minutes in, after implementing: Hermes detached (rc=3) and the job's
    "any non-zero rc means no implementation" discarded a finished change (no commit, no push, no
    PR). The tree is the evidence, so the shipped step reads it and the push/fail conditions
    follow. This runs the REAL step text against a real git repo, in both shapes.
    """
    print("\nissue #554 — a detached run's work is salvaged, not discarded")
    impl = load("issue-bot.yml")["jobs"]["implement"]
    salvage = step(impl, "Did the agent leave work behind")
    push = step(impl, "Commit + push the branch")
    fail = step(impl, "Fail loudly")

    check("salvage: the step exists and is not gated on the exit code",
          bool(salvage) and "steps.impl.outputs.rc" not in (salvage.get("if") or ""), salvage.get("if"))
    check("salvage: it reads the tree", "git status --porcelain" in (salvage.get("run") or ""), "")
    check("push: it runs when the tree is dirty, whatever the rc was",
          "steps.salvage.outputs.dirty == 'true'" in (push.get("if") or ""), push.get("if"))
    check("fail: a salvaged run is not reported as a failed implementation",
          "steps.salvage.outputs.dirty != 'true'" in (fail.get("if") or ""), fail.get("if"))

    # And the shipped step really behaves: clean tree -> dirty=false, changed tree -> dirty=true.
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / "README.md").write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "x"],
                       cwd=repo, check=True)
        script = (salvage.get("run") or "").replace("${{ steps.impl.outputs.rc }}", "3")
        for shape, mutate, want in (("clean", False, "false"), ("dirty", True, "true")):
            if mutate:
                (repo / "changed.txt").write_text("work\n")
            out = Path(td) / "gh_output"
            out.write_text("")
            subprocess.run(["bash", "-c", script], cwd=repo, check=True,
                           env=dict(os.environ, GITHUB_OUTPUT=str(out)))
            check(f"salvage: a {shape} tree reports dirty={want}",
                  f"dirty={want}" in out.read_text(), out.read_text())
            subprocess.run(["git", "checkout", "-q", "--", "."], cwd=repo, check=True)
            subprocess.run(["git", "clean", "-qfd"], cwd=repo, check=True)


def test_a_red_fix_loop_reds_the_run_and_reaches_fix_bot() -> None:
    """issue #558: a red implementation must not report success, and must be repairable.

    Measured on run 40174402542 / PR #557: the loop printed `[fix-loop] still RED after N round(s)`
    and the job still said `Fix loop against the PR branch: completed/success`, because the loop's
    exit code was captured into `green=false` and nothing acted on it. And `dispatch-fixbot` fired
    only for `ci/trending-refresh-*`, so an implementer's PR (`ci/data-gap-<n>-…`) had no repairer at
    all — the PR sat red and unmergeable until a human looked.
    """
    print("\nissue #558 — a red loop reds the run, and fix-bot can reach an implementer's PR")
    impl = load("issue-bot.yml")["jobs"]["implement"]
    names = [s.get("name") for s in steps(impl)]
    loop_at = next((i for i, n in enumerate(names) if n and "Fix loop" in n), None)
    red = step(impl, "Fail when the implementation is not green")
    check("issue-bot: the red-run step exists", bool(red), names[-6:])
    check("issue-bot: it fires exactly when the loop was not green",
          "steps.loop.outputs.green == 'false'" in (red.get("if") or ""), red.get("if"))
    check("issue-bot: it really fails the step", "exit 1" in (red.get("run") or ""), "")
    check("issue-bot: it runs AFTER the fix loop",
          loop_at is not None and (red.get("name") in names)
          and names.index(red.get("name")) > loop_at, (loop_at, red.get("name")))

    qa = load("qa-validate.yml")["jobs"]["dispatch-fixbot"]
    cond = qa.get("if") or ""
    check("qa-validate: fix-bot is dispatched for a refresh PR",
          "startsWith(github.head_ref, 'ci/trending-refresh-')" in cond, cond)
    check("qa-validate: and for an implementer's PR (ci/data-gap-…)",
          "startsWith(github.head_ref, 'ci/data-gap-')" in cond, cond)
    check("qa-validate: still only a same-repo head",
          "head.repo.full_name == github.repository" in cond, cond)
    check("qa-validate: still only on a failed validate", "failure()" in cond and "pull_request" in cond, cond)


def test_a_detached_fix_round_leaves_its_transcript_behind() -> None:
    """issue #566: rc=3 must not be a dead end — the REDACTED transcript is the artifact.

    fix-bot run 40180788039 died three times with `Input required; detached without cancelling`
    and the artifact held only `qa-report.txt`, so the question the model asked was unrecoverable
    and the next reader could only guess (which is what happened). The scrubbed agent log travels
    with the report; the RAW capture must never be the uploaded one (rule 3d).
    """
    print("\nissue #566 — a detached fix round leaves its (redacted) transcript behind")
    job = load("fix-bot.yml")["jobs"]["fix"]
    uploads = [s for s in steps(job)
               if "upload-artifact" in str(s.get("uses", ""))
               and "qa-report" in str(s.get("with", {}))]
    check("fix-bot: the QA artifact exists", bool(uploads), [s.get("name") for s in steps(job)])
    paths = " ".join(str(u.get("with", {}).get("path", "")) for u in uploads)
    check("fix-bot: it carries the scrubbed agent log", "hermes-run.scrubbed.log" in paths, paths)
    check("fix-bot: it never uploads the RAW capture", "hermes-run.log" not in paths.replace(
        "hermes-run.scrubbed.log", ""), paths)


def _makefile_commands() -> dict[str, list[str]]:
    """Every target's recipe COMMAND lines, comments and blanks skipped."""
    commands: dict[str, list[str]] = {}
    target = None
    for line in (ROOT / "Makefile").read_text().splitlines():
        if line.startswith("\t"):
            body = line.strip()
            if target and body and not body.startswith("#"):
                commands.setdefault(target, []).append(body)
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", line)
        target = m.group(1) if m else None
    return commands


def test_a_recipe_redirected_into_a_file_never_echoes_its_own_command():
    """Issue #539: `make` echoes each recipe line, and one workflow redirects a target
    straight into a file another step READS as content.

    Measured: `make issue-thread REPO=… ISSUE=… > issue.md` writes
    `python3 scripts/issue_thread.py --issue 547 --repo andyholst/trending-local-llms` as
    the FIRST line of `issue.md` — the file the implementer reads as its specification.
    The same shape would put an echoed command inside `pr-body.md`, the body GitHub parses
    for the closing keyword. A redirect into `*.log` is deliberately exempt: a log is
    captured output, and the echoed command is noise that gets scrubbed anyway.
    """

    # Given every `make <target> … > <file>` a workflow performs
    redirected: dict[str, str] = {}
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for i, line in enumerate(wf.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue  # a comment describing a command is not a redirect
            # `->` in prose and `|` pipelines are not redirects into a file
            m = re.search(r"\bmake\s+([a-z][a-z0-9-]*)[^|>]*?(?<![-\d])>>?\s*([^\s`&;]+)", line)
            if not m or "GITHUB_OUTPUT" in line:
                continue
            if m.group(2).endswith(".log"):
                continue
            redirected.setdefault(m.group(1), f"{wf.name}:{i}")

    check("make echo: a workflow redirects a make target into a file (non-vacuous)",
          bool(redirected), redirected)

    # Then  each such recipe is SILENT, so the file holds only the product's own output
    commands = _makefile_commands()
    noisy = {t: [c for c in commands.get(t, []) if not c.startswith("@")]
             for t, _where in redirected.items()}
    noisy = {t: cmds for t, cmds in noisy.items() if cmds}
    check("make echo: every redirected recipe is silenced (@), so no echoed command lands in the file",
          not noisy, noisy)

    # And   the file the implementer reads is one of them (the measured case, issue #539)
    check("make echo: `make issue-thread > issue.md` is covered by the guard",
          "issue-thread" in redirected, redirected)


def test_a_captured_recipe_is_silent():
    """Issue #562's follow-up: `OUT=$(make <target>)` captures make's ECHO too.

    Measured in production, twice (runs 40190558547, 40194644167): the sweep's
    `OUT=$(make issue-pick)` captured `python3 scripts/issue_queue.py --pick …` as its
    first line, so `PICK="${OUT#issue=}"` became that command plus the value, the step
    refused it as "not a number", and the pick job failed — the sweep implemented nothing
    for two hours. A stub `make` in a test cannot see this; the REAL recipe's echo is the
    defect, so a captured target must have a silenced recipe for the same reason a
    redirected one must.
    """
    captured: dict[str, str] = {}
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for i, line in enumerate(wf.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for m in re.finditer(r"\$\(\s*make\s+([a-z][a-z0-9-]*)|\b([a-z][a-z0-9-]*)\s*=\s*\$\(\s*make\s+([a-z][a-z0-9-]*)", line):
                target = m.group(1) or m.group(3)
                if target:
                    captured.setdefault(target, f"{wf.name}:{i}")

    check("captured make: a workflow captures a make target's stdout (non-vacuous)",
          bool(captured), captured)

    commands = _makefile_commands()
    noisy = {t: [c for c in commands.get(t, []) if not c.startswith("@")]
             for t in captured}
    noisy = {t: cmds for t, cmds in noisy.items() if cmds}
    check("captured make: every captured recipe is silenced (@), so the value is the FIRST line",
          not noisy, noisy)

    # And the measured case is one of them, so the guard cannot pass by looking elsewhere
    check("captured make: `OUT=$(make issue-pick)` is covered by the guard",
          "issue-pick" in captured, captured)


def main() -> int:
    print("workflow wiring: refresh-bot -> qa-validate -> fix-bot")
    test_every_pipeline_is_exercised_on_a_pr_or_names_its_coverage()
    test_refresh_bot()
    test_the_rebuild_decision_is_one_tested_unit()
    test_the_validate_job_checks_out_the_pr_tree_not_the_merge_result()
    test_the_closure_check_reruns_when_the_pr_body_is_edited()
    test_qa_validate()
    test_fix_bot()
    test_fix_bot_announces_its_window()
    test_fix_bot_push_behaviour()
    test_issue_bot_pr_body_actually_closes_the_issue()
    test_every_committing_bot_job_commits_as_the_agent()
    test_the_agent_identity_has_one_definition()
    test_owner_guards()
    test_guard_behaviour()
    test_guard_is_before_any_secret()
    test_every_bot_guard_with_a_cron_has_the_schedule_bypass()
    test_the_guard_registry_is_derived_from_the_tree()
    test_a_repo_event_run_is_admitted_by_its_guard()
    test_a_guarded_pipeline_gates_the_jobs_that_read_secrets()
    test_bot_verification_protocol_is_documented_and_guarded()
    test_nothing_pushes_master()
    test_auto_merge()
    test_images_follow_their_inputs()
    test_every_job_prepares_the_images_it_uses()
    test_issue_bot_push_scope_rejection()
    test_issue_bot_scrubs_the_agent_stream_before_it_reaches_the_log()
    test_issue_bot()
    test_issue_bot_asserts_the_base_it_cuts_from()
    test_no_pipeline_opens_a_draft_pr()
    test_qa_validate_runs_the_openspec_gate()
    test_secret_output_guard_wired_into_qa_validate()
    test_implement_prompt_requires_openspec_and_findings()
    test_issue_bot_files_findings_only_when_green()
    test_issue_bot_announces_its_window()
    test_the_fail_loudly_step_asks_whether_the_issue_still_needs_doing()
    test_the_queue_rule_has_one_implementation()
    test_issue_review_bot()
    test_the_reviewer_never_edits_an_issue_inside_a_window()
    test_issue_writes_use_the_default_token()
    test_a_step_that_calls_make_runs_after_the_checkout()
    test_gh_before_the_checkout_names_the_repo()
    test_unit_tests_really_run()
    test_a_job_that_runs_the_suite_checks_out_the_whole_history()
    test_issue_bot_salvages_a_detached_runs_work()
    test_a_red_fix_loop_reds_the_run_and_reaches_fix_bot()
    test_a_detached_fix_round_leaves_its_transcript_behind()
    test_a_recipe_redirected_into_a_file_never_echoes_its_own_command()
    test_a_captured_recipe_is_silent()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
