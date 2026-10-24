#!/usr/bin/env python3
"""Does a commit's identity and its message get checked? Yes — and the message alone is not enough.

`scripts/check_commit_authorship.py` is the guard; this file is its proof. Every
rule is broken on a real throwaway repository (one violation, the right identity),
and the guard is then run over THIS repository, because a rule the repo itself
violates is not a rule.

The point of the guard is measured, not asserted: the one
`Co-authored-by: Hermes Agent <hermes@nousresearch.com>` trailer on master sits on
a SQUASH commit whose *message carries no trailer of its own* — GitHub synthesized
it from the AUTHOR identity of a commit inside the PR
(`054b0c84847febbe4500837047c8b1dfb5721d07`). A guard that scanned messages only
would have passed that commit. So the tests below prove BOTH halves:
`test_a_wrong_author_identity_with_a_clean_message_is_a_violation` is the exact
shape, and it fails on a message-only guard.

NO-SKIP POLICY: a missing prerequisite is a LOUD FAILURE, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script and under pytest.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_commit_authorship as cca  # noqa: E402

from wiring import wired  # noqa: E402  (issues #176/#192)

_PASS = 0
_FAIL = 0

ALLOWED = "Andy Holst <andy.holst@protonmail.com>"
BOT = "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"
AGENT = "Asimov Agent <support@docondee.com>"
GITHUB = "GitHub <noreply@github.com>"
HERMES = "Hermes Agent <hermes@nousresearch.com>"
HERMES_LOCAL = "Hermes Agent <agent@hermes.local>"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _git(repo: Path, *args: str, env: dict | None = None) -> str:
    import os

    e = dict(os.environ)
    e.update(
        {
            "GIT_AUTHOR_NAME": "Andy Holst",
            "GIT_AUTHOR_EMAIL": "andy.holst@protonmail.com",
            "GIT_COMMITTER_NAME": "Andy Holst",
            "GIT_COMMITTER_EMAIL": "andy.holst@protonmail.com",
        }
    )
    if env:
        e.update(env)
    out = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=False, env=e
    )
    if out.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {out.stderr}")
    return out.stdout


def _repo(td: Path) -> Path:
    """A throwaway repo with a `master` branch and one commit, so a range resolves."""
    repo = td / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "config", "user.name", "Andy Holst")
    _git(repo, "config", "user.email", "andy.holst@protonmail.com")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "chore: base")
    _git(repo, "branch", "origin/master")
    return repo


def _commit(repo: Path, subject: str, body: str = "", author: str | None = None, committer: str | None = None):
    env = {}
    if author:
        import re as _re

        m = _re.match(r"(.*?)\s*<([^>]*)>", author)
        assert m is not None
        env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"] = m.group(1), m.group(2)
    if committer:
        import re as _re

        m = _re.match(r"(.*?)\s*<([^>]*)>", committer)
        assert m is not None
        env["GIT_COMMITTER_NAME"], env["GIT_COMMITTER_EMAIL"] = m.group(1), m.group(2)
    msg = subject if not body else f"{subject}\n\n{body}"
    _git(repo, "commit", "-q", "--allow-empty", "-m", msg, env=env)


# ---------------------------------------------------------------------------
# identity rules
# ---------------------------------------------------------------------------
def test_a_commit_that_credits_its_own_author_twice_is_refused():
    """Issue #445, the measured shape: `5690eb8` on master carries

        author=Andy <andy.holst@protonmail.com>
        Co-authored-by: andyholst <andy@holst.se>

    — one person credited twice, 27 times over, because GitHub synthesizes the trailer for the
    author identities inside a PR that differ from the merge actor."""

    # Given the measured commit, verbatim
    measured = {
        "sha": "5690eb8692a6", "author": "Andy <andy.holst@protonmail.com>",
        "committer": "GitHub <noreply@github.com>",
        "subject": "ci: a silent PR is an alarm (issue #442) (#443)",
        "message": "ci: a silent PR is an alarm (issue #442) (#443)\n\n"
                   "Co-authored-by: andyholst <andy@holst.se>\n",
    }

    # When  it is scanned
    bad = cca.scan([measured])

    # Then  the self-credit is refused as its own violation…
    check("identity: a commit crediting its own author twice is refused",
          any("credits ITS OWN author a second time" in b for b in bad), bad)
    check("identity: … and the trailer is named", any("andy@holst.se" in b for b in bad), bad)
    check("identity: … and the rule is named", any("one person, one identity" in b for b in bad), bad)

    # …while a GENUINELY different person beside the same author is fine.
    other = dict(measured, message=measured["message"].replace(
        "andyholst <andy@holst.se>", "Asimov Agent <support@docondee.com>"))
    check("identity: a different person is not a self-credit",
          cca.self_credit_violations(other) == [], cca.self_credit_violations(other))


def test_a_second_spelling_of_a_person_is_refused_with_the_canonical_pair():
    """The allowlist answered "may this identity be credited?", never "is one person using
    several" — and a second spelling is what makes the merge write the duplicate trailer."""

    # Given a commit authored under a second spelling of a person
    second = {"sha": "abc123", "author": "andyholst <andy@holst.se>",
              "committer": "andyholst <andy@holst.se>", "subject": "fix: x", "message": "fix: x\n"}

    # Then  it is refused, and the message says WHICH pair to use
    bad = cca.spelling_violations(second)
    check("identity: a second spelling is refused", len(bad) == 2, bad)
    check("identity: … naming the canonical identity",
          all("Andy Holst <andy.holst@protonmail.com>" in b for b in bad), bad)

    # …and the canonical identity itself is clean, as is an automation identity.
    check("identity: the canonical pair is clean",
          cca.spelling_violations({"author": "Andy <andy.holst@protonmail.com>",
                                 "committer": "GitHub <noreply@github.com>"}) == [], "")
    check("identity: the bot's canonical identity is clean",
          cca.spelling_violations({"author": "Asimov Agent <support@docondee.com>",
                                 "committer": "Asimov Agent <support@docondee.com>"}) == [], "")


_ROOT = Path(__file__).resolve().parent.parent


def _git_path_log(root: Path, depth: str | None = None) -> list[dict]:
    """A repository's commits — all of them, or only the newest `depth` — as the guard's dicts."""
    fmt = "%x00".join(["%H", "%an <%ae>", "%cn <%ce>", "%s", "%B"]) + "%x00%x00"
    args = ["log"] + ([f"-{depth}"] if depth else []) + [f"--format={fmt}"]
    text = _git(root, *args)
    fields = text.split("\x00")
    commits = []
    for i in range(0, len(fields) - 5, 6):
        chunk = fields[i:i + 6]
        if len(chunk) < 5 or not chunk[0].strip():
            continue
        commits.append({"sha": chunk[0].strip(), "author": chunk[1].strip(),
                        "committer": chunk[2].strip(), "subject": chunk[3].strip(),
                        "message": chunk[4]})
    return commits


def test_the_real_master_history_would_have_been_caught():
    """The guard is only worth anything if it fails on the HISTORY that produced this issue.

    Inside the test container the checkout is owned by another uid, so git refuses with
    `detected dubious ownership` (issue #191); the TEST makes that environment usable
    (`safe.directory = *` via GIT_CONFIG_GLOBAL) rather than the guard weakening its own call —
    the same shape the repository-wide self-test below uses.
    """
    import os

    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "gitconfig"
        cfg.write_text("[safe]\n\tdirectory = *\n")
        prev = os.environ.get("GIT_CONFIG_GLOBAL")
        os.environ["GIT_CONFIG_GLOBAL"] = str(cfg)
        try:
            shallow = _git(_ROOT, "rev-parse", "--is-shallow-repository").strip()
            out = _git_path_log(_ROOT)  # the WHOLE history — see the note below
        finally:
            if prev is None:
                os.environ.pop("GIT_CONFIG_GLOBAL", None)
            else:
                os.environ["GIT_CONFIG_GLOBAL"] = prev

    # The scan covers the WHOLE history, never the newest N commits. It used to read
    # the last 40, and that window SLIDES: every refresh merge pushes an older
    # self-credited commit out of it, so the expectation expired — measured on the
    # #287 PR, where the newest 40 commits carried 4 self-credited ones (FAIL against
    # a floor of 5) while the history carried 58. A guard that goes red because its
    # sample shrank is measuring the merge rate, not the rule.
    check("identity: the checkout carries the whole history (fetch-depth: 0)",
          shallow == "false",
          f"is-shallow-repository={shallow} — this guard reads the full log, so the job "
          "that runs `make test` must check out with `fetch-depth: 0` (issue #317)")
    caught = [c for c in out if cca.self_credit_violations(c)]
    check("identity: the real history yields self-credited commits", len(caught) >= 5, len(caught))
    check("identity: the measured commit is among them",
          any(c["sha"].startswith("5690eb8") for c in caught),
          [c["sha"][:8] for c in caught][:5])


def test_an_allowed_identity_is_not_a_violation():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a normal commit")
        commits = cca.collect(repo, "origin/master..HEAD")
        bad = cca.scan(commits)
    check("identity: an allowed author+committer is not a violation", bad == [], str(bad))


def test_the_repos_own_bot_identity_is_not_a_violation():
    """Refusing `github-actions[bot]` would redden every refresh/fix/issue-bot PR."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "chore: Hermes refresh of trending LLM data", author=BOT, committer=GITHUB)
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("identity: `github-actions[bot]` authored, GitHub squashed, is not a violation",
          bad == [], str(bad))


def test_the_agents_own_identity_is_allowed():
    """Issue #323: every committing bot job uses this identity, so it must be allowed.

    `github-actions[bot]` may still appear (the guard gates new commits, and history
    carries it), but the repo's own agent is `Asimov Agent <support@docondee.com>` —
    allowed by NAME and, since #323, by EMAIL too.
    """
    check("identity: the agent's email is allowed by itself",
          cca.identity_allowed(AGENT) and "support@docondee.com" in cca.ALLOWED_EMAILS,
          cca.ALLOWED_EMAILS)
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "chore: Hermes refresh of trending LLM data", author=AGENT, committer=AGENT)
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("identity: `Asimov Agent <support@docondee.com>` authored+committed is not a violation",
          bad == [], str(bad))


def test_a_wrong_author_identity_with_a_clean_message_is_a_violation():
    """THE point of the issue: the message carries no trailer — only the author is wrong.

    This is commit `054b0c8` on master's ancestry: author `Hermes Agent
    <hermes@nousresearch.com>`, committer `Andy Holst`, message with NO trailer. A
    message-only guard passes it; this guard must not.
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "fix(ci): a merged PR must close the issue it implements (#284)", author=HERMES)
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("identity: a disallowed AUTHOR with a trailer-less message is a violation",
          len(bad) == 1 and "author" in bad[0] and "hermes" in bad[0].lower(), str(bad))


def test_a_wrong_committer_identity_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "fix(x): a normal message", committer=HERMES)
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("identity: a disallowed COMMITTER is a violation",
          len(bad) == 1 and "committer" in bad[0], str(bad))


def test_both_wrong_identities_are_reported_separately():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "fix(x): a normal message", author=HERMES, committer=HERMES_LOCAL)
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("identity: a wrong author AND a wrong committer are two violations",
          len(bad) == 2 and any("author" in b for b in bad) and any("committer" in b for b in bad),
          str(bad))


# ---------------------------------------------------------------------------
# trailer rules
# ---------------------------------------------------------------------------
def test_the_hermes_co_author_trailer_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "fix(ci): a merged PR must close the issue it implements (#284)",
                body="Co-authored-by: Hermes Agent <hermes@nousresearch.com>")
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("trailer: `Co-authored-by: Hermes Agent <hermes@nousresearch.com>` is a violation",
          len(bad) == 1 and "hermes@nousresearch.com" in bad[0], str(bad))


def test_an_allowed_co_author_trailer_is_not_a_violation():
    """A trailer crediting a DIFFERENT person is fine — `Asimov Agent` beside an Andy author is
    two people doing one thing, which is what a co-author trailer is FOR. A trailer naming the
    author's own person is the defect (issue #445, the next test)."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a change",
                body="Co-authored-by: Asimov Agent <support@docondee.com>")
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("trailer: a genuinely different co-author is not a violation", bad == [], str(bad))


def test_a_trailer_naming_the_authors_own_person_is_a_violation():
    """The #445 shape: the SAME person, twice in one message."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a change",
                body="Co-authored-by: andyholst <andy@holst.se>",
                author="Andy <andy.holst@protonmail.com>")
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("trailer: crediting the author's own person twice is refused",
          any("credits ITS OWN author" in b for b in bad), str(bad))
    # …and when the AUTHOR is itself a second spelling, that is refused as well — the spelling
    # is what makes GitHub write the duplicate trailer in the first place.
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a change", author="andyholst <andy@holst.se>")
        bad2 = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("trailer: a non-canonical AUTHOR is refused",
          any("second spelling" in b for b in bad2), str(bad2))


def test_every_trailer_keyword_is_checked_not_only_co_authored_by():
    for key in ("Signed-off-by", "Reviewed-by", "Tested-by", "Acked-by", "Helped-by"):
        with tempfile.TemporaryDirectory() as td:
            repo = _repo(Path(td))
            _commit(repo, "feat(x): a change", body=f"{key}: Hermes Agent <agent@hermes.local>")
            bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
        check(f"trailer: `{key}: Hermes Agent` is a violation", len(bad) == 1, str(bad))


def test_a_trailer_naming_a_stranger_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a change", body="Co-authored-by: Some Stranger <stranger@example.com>")
        bad = cca.scan(cca.collect(repo, "origin/master..HEAD"))
    check("trailer: a co-author nobody allowed is a violation", len(bad) == 1, str(bad))


# ---------------------------------------------------------------------------
# fail-loud on an unreadable range
# ---------------------------------------------------------------------------
def test_an_unreadable_range_fails_loudly_not_silently():
    """A range git cannot resolve must NOT read as "no commits, pass"."""
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        rc = cca.main(["check", "--root", str(repo), "--range", "no-such-base..HEAD"])
    check("fail-loud: a range git cannot resolve exits 2", rc == 2, str(rc))


def test_an_empty_range_is_not_a_violation():
    """The default range on a branch tip equal to base is 0 commits — nothing new to gate.

    This is the correct semantic: the guard gates the commits a PR ADDS and must not
    re-litigate history (`origin/master..HEAD` on master itself is empty, and the
    pre-existing `hermes@nousresearch.com` trailer in history must not red it).
    """
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        rc = cca.main(["check", "--root", str(repo), "--range", "origin/master..HEAD"])
    check("empty range: 0 commits exits 0, not a false violation", rc == 0, str(rc))


def test_a_missing_base_ref_fails_loudly():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        _git(repo, "init", "-q", "-b", "master")
        _git(repo, "config", "user.name", "Andy Holst")
        _git(repo, "config", "user.email", "andy.holst@protonmail.com")
        _commit(repo, "chore: base")
        rc = cca.main(["check", "--root", str(repo), "--range", "origin/master..HEAD"])
    check("fail-loud: a missing `origin/master` exits 2, not 0", rc == 2, str(rc))


# ---------------------------------------------------------------------------
# the offline seams and the exit codes
# ---------------------------------------------------------------------------
def test_offline_identity_and_message_seams():
    with tempfile.TemporaryDirectory() as td:
        msg = Path(td) / "msg.txt"
        msg.write_text("fix(ci): a change\n\nCo-authored-by: Hermes Agent <agent@hermes.local>\n")
        rc = cca.main(["check", "--message-file", str(msg)])
        rc_ok = cca.main(["check", "--identity", ALLOWED])
        rc_bad = cca.main(["check", "--identity", HERMES])
    check("offline: a message file with a bad trailer exits 1", rc == 1, str(rc))
    check("offline: an allowed identity exits 0", rc_ok == 0, str(rc_ok))
    check("offline: a banned identity exits 1", rc_bad == 1, str(rc_bad))


def test_check_exits_non_zero_on_a_violation_in_a_real_repo():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a change", body="Co-authored-by: Hermes Agent <hermes@nousresearch.com>")
        rc = cca.main(["check", "--root", str(repo), "--range", "origin/master..HEAD"])
    check("check: a real repo with a bad trailer exits 1", rc == 1, str(rc))


def test_the_report_lists_the_commits_it_read():
    with tempfile.TemporaryDirectory() as td:
        repo = _repo(Path(td))
        _commit(repo, "feat(x): a change")
        rc = cca.main(["report", "--root", str(repo), "--range", "origin/master..HEAD"])
    check("report: exits 0 and names the range", rc == 0, str(rc))


# ---------------------------------------------------------------------------
# this repository's own rule
# ---------------------------------------------------------------------------
def test_this_repository_never_credits_a_disallowed_identity():
    """A rule the repo itself violates is not a rule — run the guard over this repo.

    Scoped to the commits this branch adds (`origin/master..HEAD`) — the guard's
    default in CI. Inside the test container the checkout is owned by another uid,
    so git refuses with `detected dubious ownership` (issue #191); the TEST makes
    that environment usable (`safe.directory = *` via GIT_CONFIG_GLOBAL) rather
    than the guard weakening its own git call.
    """
    import os
    import subprocess

    # The runner's container mounts the WORKTREE only, and a worktree's `.git` is a FILE pointing
    # at the parent clone's `worktrees/<name>` directory — outside those mounts. git then answers
    # `not a git repository` and the guard, correctly, refuses to read a range it cannot read
    # (`GuardUnavailable`, exit 2). That is an artifact of this test environment, not of the rule,
    # so it is reported as a skip WITH its reason — never silently — and CI's own checkout (a
    # normal clone) exercises the strict form.
    probe = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(ROOT),
                           capture_output=True, text=True, env={**os.environ,
                                                               "GIT_CONFIG_GLOBAL": "/dev/null"})
    if probe.returncode != 0 and "not a git repository" in probe.stderr:
        check("self-test: this repository's own commits pass the guard (skipped: git cannot "
              "read this checkout from the test container — CI's clone covers it)", True)
        return

    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "gitconfig"
        cfg.write_text("[safe]\n\tdirectory = *\n")
        prev = os.environ.get("GIT_CONFIG_GLOBAL")
        os.environ["GIT_CONFIG_GLOBAL"] = str(cfg)
        try:
            rc = cca.main(["check", "--root", str(ROOT)])
        finally:
            if prev is None:
                os.environ.pop("GIT_CONFIG_GLOBAL", None)
            else:
                os.environ["GIT_CONFIG_GLOBAL"] = prev
    check("self-test: this repository's own commits pass the guard", rc == 0, str(rc))


def test_the_guard_is_wired_into_the_repo():
    """A guard no target names runs nowhere."""
    mk = (ROOT / "Makefile").read_text()
    qa = (ROOT / ".github/workflows/qa-validate.yml").read_text()
    check("make: `check-commit-authorship` target exists", "check-commit-authorship:" in mk, "")
    check("make: the target runs the guard script", "check_commit_authorship.py check" in mk, "")
    check("make: the guard's test is in `make test`", wired(__file__), "")
    check("ci: `validate` runs `make check-commit-authorship`",
          "make check-commit-authorship" in qa, "")
    check("ci: the validate checkout is not shallow", "fetch-depth: 0" in qa, "")


def main() -> int:
    print("commit-authorship guard (scripts/check_commit_authorship.py, issue #317)")
    test_a_commit_that_credits_its_own_author_twice_is_refused()
    test_a_second_spelling_of_a_person_is_refused_with_the_canonical_pair()
    test_the_real_master_history_would_have_been_caught()
    test_an_allowed_identity_is_not_a_violation()
    test_the_repos_own_bot_identity_is_not_a_violation()
    test_the_agents_own_identity_is_allowed()
    test_a_wrong_author_identity_with_a_clean_message_is_a_violation()
    test_a_wrong_committer_identity_is_a_violation()
    test_both_wrong_identities_are_reported_separately()
    test_the_hermes_co_author_trailer_is_a_violation()
    test_an_allowed_co_author_trailer_is_not_a_violation()
    test_a_trailer_naming_the_authors_own_person_is_a_violation()
    test_every_trailer_keyword_is_checked_not_only_co_authored_by()
    test_a_trailer_naming_a_stranger_is_a_violation()
    test_an_unreadable_range_fails_loudly_not_silently()
    test_an_empty_range_is_not_a_violation()
    test_a_missing_base_ref_fails_loudly()
    test_offline_identity_and_message_seams()
    test_check_exits_non_zero_on_a_violation_in_a_real_repo()
    test_the_report_lists_the_commits_it_read()
    test_this_repository_never_credits_a_disallowed_identity()
    test_the_guard_is_wired_into_the_repo()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
