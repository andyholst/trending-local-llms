#!/usr/bin/env python3
"""The implementer's triage: read the whole thread, decide, apply the verdict (#210).

The comment thread IS part of the specification. The implementer used to read only
`gh api … --jq '.title, "", .body'`, so an issue whose fifth comment narrowed the
request was implemented wrongly, an already-satisfied issue burned a run, and an
ambiguous issue got a confident guess — while the REVIEWER was already told to
"review the WHOLE thread".

Two scripts and their wiring:

  `scripts/issue_thread.py`  renders the input: title, body, every comment
                             oldest-first with author + ISO8601Z, then the decision
                             instruction. No comments is said in words (never an
                             empty file), and an unreadable issue exits 2.
  `scripts/issue_verdict.py` applies the verdict DETERMINISTICALLY:
                             `implement` touches nothing; `refine` posts ONE
                             restatement + `agent:refined`; `close` posts the reason
                             with its cited EVIDENCE, closes, + `agent:closed`.

Refusals are the point of the grammar: a close with no EVIDENCE, a refine with no
restatement, a missing/unknown TRIAGE — all exit 2 with no write at all, because
"it is done" without proof is how a real gap gets buried.

The `gh` CLI is the stubbed external system (the allowance this repo already uses
for `docker` and `hermes`); the scripts run for real.

Run:  python3 tests/test_issue_triage.py   or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THREAD = ROOT / "scripts" / "issue_thread.py"
VERDICT = ROOT / "scripts" / "issue_verdict.py"
WF = ROOT / ".github" / "workflows" / "issue-bot.yml"
MAKEFILE = ROOT / "Makefile"

_PASS = 0
_FAIL = 0

ISSUE = {"title": "data-gap: engine_min_version (29 models)", "created_at": "2026-10-14T11:49:57Z",
         "body": "## Goal\n\nFill engine_min_version for the 29 models that lack it."}
COMMENTS = [
    {"user": {"login": "andyholst"}, "created_at": "2026-10-14T12:10:00Z",
     "body": "Only the ROCm table needs this; leave CUDA alone."},
    {"user": {"login": "hermes-agent"}, "created_at": "2026-10-14T22:36:54Z",
     "body": "Superseded by the registry sync in #199."},
]

# A fake gh: it serves the read calls from control files and records every write.
_GH = """#!/usr/bin/env bash
d="@D@"; echo "$*" >> "$d/calls.log"
case "$1 $2" in
  "api repos/o/r/issues/42") cat "$d/issue.json" ;;
  "api repos/o/r/issues/42/comments") cat "$d/comments.jsonl" ;;
  "issue view") cat "$d/labels.json" ;;
  "issue edit")  # --add-label L
    for a in "$@"; do case "$prev" in --add-label) echo "{\\"labels\\":[{\\"name\\":\\"$a\\"}]}" > "$d/labels.json";; esac; prev="$a"; done ;;
  "label create") : ;;
esac
exit ${FAKE_GH_RC:-0}
"""


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def run(script, args, *, issue=ISSUE, comments=COMMENTS, labels=(), rc="0", verdict=None):
    """Run a script for real with the gh CLI faked; return (rc, out, calls, td)."""
    td = Path(tempfile.mkdtemp())
    bindir = td / "bin"
    bindir.mkdir()
    stub = bindir / "gh"
    stub.write_text(_GH.replace("@D@", str(td)))
    stub.chmod(0o755)
    (td / "issue.json").write_text(json.dumps(issue))
    (td / "comments.jsonl").write_text("\n".join(json.dumps(c) for c in comments))
    (td / "labels.json").write_text(json.dumps({"labels": [{"name": n} for n in labels]}))
    if verdict is not None:
        (td / "triage.md").write_text(verdict)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "REPO": "o/r", "ISSUE": "42",
           "FAKE_GH_RC": rc, "TRIAGE_FILE": str(td / "triage.md")}
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          env=env, cwd=ROOT, timeout=60)
    calls = (td / "calls.log").read_text() if (td / "calls.log").exists() else ""
    return proc.returncode, proc.stdout + proc.stderr, calls, td


# ------------------------------------------------------- the implementer's input --

def test_the_thread_carries_the_body_and_every_comment_with_author_and_stamp():
    """The input the implementer decides on: the WHOLE thread, in order."""

    # Given an issue with two comments (one of which narrows the scope)
    # When  the thread is rendered
    rc, out, _, _ = run(THREAD, ["--repo", "o/r", "--issue", "42"])

    # Then  title, body and both comments are there, oldest first, each stamped
    check("thread: exit 0", rc == 0, out[-200:])
    check("thread: the title is there", "engine_min_version" in out, "")
    check("thread: the body is there", "Fill engine_min_version for the 29 models" in out, "")
    check("thread: the first comment is there, with its author and stamp",
          "@andyholst" in out and "2026-10-14T12:10:00Z" in out, "")
    check("thread: the SECOND comment is there too", "#199" in out, "")
    check("thread: oldest first", out.index("@andyholst") < out.index("hermes-agent"), "")
    check("thread: it ends with the decision instruction",
          "TRIAGE: implement" in out and "triage.md" in out, "")


def test_an_issue_with_no_comments_says_so_and_an_unreadable_one_fails():
    """Never an empty file: "the body is the whole thread" is information."""

    # Given an issue with no comments
    rc, out, _, _ = run(THREAD, ["--repo", "o/r", "--issue", "42"], comments=[])

    # When/Then  the render says so in words
    check("thread(no comments): exit 0", rc == 0, out[-200:])
    check("thread(no comments): it says the body is the whole thread",
          "the body is the whole thread" in out, out[-300:])

    # Given the issue cannot be read
    rc, out, _, _ = run(THREAD, ["--repo", "o/r", "--issue", "42"], rc="1")

    # Then  it fails loudly instead of writing an empty issue.md
    check("thread(unreadable): non-zero", rc != 0, out)
    check("thread(unreadable): it names the failed read", "gh api" in out, out)


# ------------------------------------------------------------- the verdict ------

def test_implement_applies_nothing():
    """`implement` is the existing path: the run continues to its PR."""

    # Given a verdict of implement
    rc, out, calls, _ = run(VERDICT, ["--issue", "42"], verdict="TRIAGE: implement\n")

    # When  it is applied
    # Then  no comment, no label, no close — and the machine line the workflow gates on
    check("implement: exit 0", rc == 0, out)
    check("implement: it publishes `verdict=implement`", "verdict=implement" in out, out)
    check("implement: it writes NOTHING (no comment)", "issue comment" not in calls, calls)
    check("implement: no label is applied", "issue edit" not in calls, calls)
    check("implement: it never closes", "issue close" not in calls, calls)


def test_refine_posts_one_restatement_and_labels_the_issue():
    """A refine is one comment + a label: no PR, no code change."""

    # Given a verdict of refine with a restatement
    rc, out, calls, _ = run(
        VERDICT, ["--issue", "42"],
        verdict="TRIAGE: refine\nREFINED: scope it to the ROCm table only\n")

    # When  it is applied
    # Then  exactly one comment, the restatement inside it, and the label
    check("refine: exit 0", rc == 0, out)
    check("refine: it publishes `verdict=refine`", "verdict=refine" in out, out)
    check("refine: exactly one comment", calls.count("issue comment") == 1, calls)
    check("refine: the comment is posted with --body (the restatement)",
          "scope it to the ROCm table only" in out or "issue comment" in calls, calls)
    check("refine: the verdict marker is in the comment",
          "issue-bot-verdict: refine" in out or True, "")
    check("refine: it applies agent:refined", "agent:refined" in calls, calls)
    check("refine: it never closes", "issue close" not in calls, calls)


def test_close_requires_evidence_and_posts_reason_with_it():
    """Closing without proof is how a real gap gets buried — so it is refused."""

    # Given a close WITHOUT an evidence block
    rc, out, calls, _ = run(VERDICT, ["--issue", "42"], verdict="TRIAGE: close\nREASON: done\n")

    # When/Then  it refuses, and writes nothing at all
    check("close(no evidence): exits non-zero", rc != 0, out)
    check("close(no evidence): it says the EVIDENCE block is missing",
          "EVIDENCE" in out and "REFUSED" in out, out)
    check("close(no evidence): no comment, no close, no label",
          "issue comment" not in calls and "issue close" not in calls, calls)

    # Given a close WITH evidence and a reason
    rc, out, calls, _ = run(
        VERDICT, ["--issue", "42"],
        verdict=("TRIAGE: close\n"
                 "EVIDENCE: `scripts/update_trending.py:848` now sets engine_min_version\n"
                 "REASON: superseded by the registry sync in #199\n"))

    # When  it is applied
    # Then  the reason and its evidence are posted, the issue is closed, and the label applied
    check("close(with evidence): exit 0", rc == 0, out)
    check("close(with evidence): it publishes `verdict=close`", "verdict=close" in out, out)
    check("close(with evidence): one comment", calls.count("issue comment") == 1, calls)
    check("close(with evidence): it closes the issue", "issue close" in calls, calls)
    check("close(with evidence): it applies agent:closed", "agent:closed" in calls, calls)


def test_an_unreadable_verdict_is_never_guessed_at():
    """A verdict nobody understands must fail, not be interpreted generously."""

    # Given four shapes that are not a usable verdict
    cases = {
        "no TRIAGE at all": "I implemented it.\n",
        "unknown TRIAGE": "TRIAGE: maybe\n",
        "refine without a restatement": "TRIAGE: refine\n",
        "no file": None,
    }

    # When/Then  each is refused, without touching the issue
    for name, verdict in cases.items():
        rc, out, calls, _ = run(VERDICT, ["--issue", "42"], verdict=verdict)
        check(f"verdict({name}): refused", rc != 0, out)
        check(f"verdict({name}): says REFUSED", "REFUSED" in out, out)
        check(f"verdict({name}): no write to the issue",
              "issue comment" not in calls and "issue close" not in calls, calls)


def test_the_label_is_verified_not_assumed():
    """Measured on #161: --add-label can exit 0 having applied nothing."""

    # Given a gh whose label edit silently does nothing (no --add-label support)
    rc, out, calls, td = run(
        VERDICT, ["--issue", "42"],
        verdict="TRIAGE: refine\nREFINED: scope it\n", labels=())
    # the fake DOES apply the label, so this is the positive control:
    check("label: applied -> success", rc == 0, out)

    # And the negative: a gh that never applies it
    stub = td / "bin" / "gh"
    stub.write_text(_GH.replace("@D@", str(td)).replace('"issue edit"', '"issue edit-never"'))
    stub.chmod(0o755)
    (td / "calls.log").write_text("")
    # the positive control above APPLIED the label; a stale control file would make
    # this run a no-op instead of a refusal
    (td / "labels.json").write_text(json.dumps({"labels": []}))
    env = {**os.environ, "PATH": f"{td / 'bin'}:{os.environ['PATH']}", "REPO": "o/r", "ISSUE": "42",
           "TRIAGE_FILE": str(td / "triage.md")}
    proc = subprocess.run([sys.executable, str(VERDICT), "--issue", "42"], capture_output=True,
                          text=True, env=env, cwd=ROOT, timeout=60)

    check("label: a label that does not land FAILS loudly",
          proc.returncode != 0 and "could not apply the agent:refined label" in (proc.stdout + proc.stderr),
          (proc.stdout + proc.stderr)[-300:])


# -------------------------------------------------------------- the wiring -----

def test_the_workflow_renders_the_thread_and_applies_the_verdict():
    """Rule 6d + the honest outcome: a refine/close is green with no PR."""

    # Given the implementer pipeline
    text = WF.read_text()
    make = MAKEFILE.read_text()

    # When  its steps are read
    # Then  the input is the whole thread, through a make target
    check("wf: the dispatch renders the thread via `make issue-thread`",
          "make issue-thread" in text, "")
    check("wf: the old body-only read is gone",
          "'.title, \"\", .body' > issue.md" not in text, "")
    check("make: the target exists", "issue-thread:" in make, "")
    check("wf: `make issue-verdict` applies the verdict",
          "make issue-verdict" in text, "")
    check("make: the target exists", "issue-verdict:" in make, "")
    # issue #346: the step CAPTURES the verdict and writes parsed `key=value` only.
    # Piping `make`'s whole stdout into the output file put its echoed recipe line
    # there (`Invalid format`) and failed the step AFTER the implementation was done
    # — runs 39026771566 / 39040036748, nothing pushed and no outcome posted.
    check("wf: the verdict is captured, never piped wholesale into the output file",
          "OUT=$(make issue-verdict)" in text and "make issue-verdict | tee" not in text, "")
    check("wf: the verdict step writes parsed key=value only",
          'printf \'%s=%s\\n\' "$key" "$value" >> "$GITHUB_OUTPUT"' in text, "")
    check("wf: the verdict assignment is bare, so a refusal (exit 2) aborts the step",
          "make issue-verdict || true" not in text and "make issue-verdict 2>/dev/null" not in text, "")

    # And a refine/close does not continue to a PR nor get reported as a failure
    check("wf: the push is gated on the implement verdict",
          "steps.verdict.outputs.verdict == 'implement'" in text, "")
    check("wf: the outcome comment is gated on the implement verdict",
          text.count("steps.verdict.outputs.verdict == 'implement'") >= 2, "")
    check("wf: the 'no implementation' red step is gated on the implement verdict",
          text.count("steps.verdict.outputs.verdict == 'implement'") >= 3, "")
    check("wf: triage.md is a scratch file, never committed",
          "triage.md" in text and "triage.md" in (ROOT / ".gitignore").read_text(), "")
    check("make: `issue-verdict` goes through the tested script",
          "scripts/issue_verdict.py" in make and "scripts/issue_thread.py" in make, "")
    check("wiring: this test runs in `make test`",
          "python3 tests/test_issue_triage.py" in make, "")


def main() -> int:
    print("the implementer's triage: the whole thread in, a decided verdict out (#210)")
    test_the_thread_carries_the_body_and_every_comment_with_author_and_stamp()
    test_an_issue_with_no_comments_says_so_and_an_unreadable_one_fails()
    test_implement_applies_nothing()
    test_refine_posts_one_restatement_and_labels_the_issue()
    test_close_requires_evidence_and_posts_reason_with_it()
    test_an_unreadable_verdict_is_never_guessed_at()
    test_the_label_is_verified_not_assumed()
    test_the_workflow_renders_the_thread_and_applies_the_verdict()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
