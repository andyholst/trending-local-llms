#!/usr/bin/env python3
"""commit-authorship guard — `make check-commit-authorship` (issue #317).

Nothing read a commit's message or a commit's identity. `make secret-scan`
(gitleaks) reads credential VALUES; `make check-secret-output` reads run-time leak
SHAPES; `make pr-closure` reads the PR BODY. So a commit that credits anyone at
all landed silently — and it already has:

    $ git log --all --format='%B' | grep -i '^co-authored-by:' | sort | uniq -c
         32 Co-authored-by: github-actions[bot] <41898282+github-actions[bot]@...>
         22 Co-authored-by: andyholst <andyholst@users.noreply.github.com>
         10 Co-authored-by: Hermes Agent <agent@hermes.local>
          6 Co-authored-by: asimov <asimov@omarchy.local>
          2 Co-authored-by: asimov <asimov@example.com>
          2 Co-authored-by: asimov-agent <asimov-agent@users.noreply.github.com>
          1 Co-authored-by: Hermes Agent <hermes@nousresearch.com>

The only identities on this repo are **Andy Holst** and **Asimov Agent**. The
repo's own automation identities are also allowed, because refusing them would
redden every bot PR: `github-actions[bot]` (the `git config` in refresh-bot,
fix-bot and issue-bot) and `GitHub <noreply@github.com>` (the committer GitHub
uses for a squash). Everything else is refused; `Hermes Agent` is named in the
failure.

WHY THE MESSAGE ALONE IS NOT ENOUGH (measured, not inferred)
------------------------------------------------------------
The one `hermes@nousresearch.com` trailer on master sits on a SQUASH commit:

    $ git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>%n%B' 4a4d78b
    author=Andy <andy.holst@protonmail.com>
    committer=GitHub <noreply@github.com>
    fix(ci): a merged PR must close the issue it implements (#284) (#285)

    Co-authored-by: Hermes Agent <hermes@nousresearch.com>

Its subject carries BOTH `(#284)` and `(#285)` — the GitHub squash format
(`<PR title> (#<PR number>)`) — and its committer is GitHub. The trailer was
SYNTHESIZED at merge time from the AUTHOR IDENTITY of a commit inside the PR:

    $ git log --all --format='%H|%an|%ae|%s' --author='hermes@nousresearch.com'
    054b0c84847febbe4500837047c8b1dfb5721d07|Hermes Agent|hermes@nousresearch.com|fix(ci): a merged PR must close the issue it implements (#284)

That commit's message has NO trailer — only its author is wrong. A guard that
scanned messages only would have passed it and the trailer would still have
landed on master. So this guard checks BOTH:

  1. the AUTHOR and COMMITTER identity of every commit in the range, and
  2. the `Co-authored-by:`-class trailers in every commit message.

Existing history is NOT rewritten: the guard gates NEW commits, so its default
range is `origin/master..HEAD` — the commits a PR adds. A range that cannot be
resolved (a shallow clone, a missing ref) FAILS LOUDLY; it never degrades to
"no commits, pass".
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: Trailer keywords that credit a person. `Co-authored-by` is the one GitHub
#: synthesizes at squash time; the rest are the same class and cost nothing.
TRAILER_KEYWORDS = (
    "co-authored-by",
    "signed-off-by",
    "reviewed-by",
    "tested-by",
    "acked-by",
    "helped-by",
)

TRAILER_RE = re.compile(
    r"^\s*(?P<key>" + "|".join(TRAILER_KEYWORDS) + r")\s*:\s*(?P<who>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

#: `Name <email>` — the shape git prints and a trailer carries.
IDENTITY_RE = re.compile(r"^(?P<name>.*?)\s*<(?P<email>[^<>]*)>\s*$")

#: The identities this repo allows. Names are matched case-insensitively after
#: whitespace is collapsed; `github-actions[bot]` and `GitHub` are the repo's own
#: automation (see the module docstring for why they cannot be refused).
# The identity's ONE definition (issue #325): the name/email every committing job uses and
# the sets this guard accepts. A hand-kept copy here was the fifth place to edit.
from agent_identity import (AGENT_EMAIL, AGENT_NAME, ALLOWED_EMAILS, ALLOWED_NAMES,  # noqa: E402
                            canonical_for, person_of)

#: Refused even when the name or the email is allowed: an identity that CLAIMS
#: to be Hermes is the exact leak this guard exists for (issue #317).
BANNED = re.compile(r"hermes", re.IGNORECASE)

#: The default range: the commits a PR adds on top of the fetched base.
DEFAULT_RANGE = "origin/master..HEAD"


class GuardUnavailable(Exception):
    """The range could not be read — a defect, never a silent pass."""


def _norm(value: str) -> str:
    return " ".join(value.split()).lower()


def split_identity(raw: str) -> tuple[str, str]:
    """`Andy Holst <a@b>` -> `("Andy Holst", "a@b")`; a bare string is a name."""
    m = IDENTITY_RE.match(raw.strip())
    if not m:
        return raw.strip(), ""
    return m.group("name").strip(), m.group("email").strip()


def identity_allowed(raw: str) -> bool:
    """True when an author/committer identity is one this repo allows."""
    name, email = split_identity(raw)
    if BANNED.search(name) or BANNED.search(email):
        return False
    return _norm(name) in ALLOWED_NAMES or _norm(email) in ALLOWED_EMAILS


def trailer_violations(message: str) -> list[str]:
    """Every crediting trailer in a commit message whose identity is not allowed."""
    bad: list[str] = []
    for m in TRAILER_RE.finditer(message):
        who = m.group("who")
        if not identity_allowed(who):
            bad.append(f"{m.group('key')}: {who}")
    return bad


def self_credit_violations(commit: dict) -> list[str]:
    """Trailers that credit the SAME PERSON as the commit's author or committer (issue #445).

    GitHub synthesizes a `Co-authored-by:` for every author inside a squashed PR that differs
    from the merge actor — so a PR whose commits use a SECOND SPELLING of the person who
    merges lands a commit that credits that person twice:

        author=Andy <andy.holst@protonmail.com>
        Co-authored-by: andyholst <andy@holst.se>

    27 commits on master read exactly like that. A genuinely different person (Asimov Agent
    beside an Andy author) is fine — this only refuses a message that repeats its own author.
    """
    people = {p["name"] for p in (person_of(commit.get("author", "")),
                                  person_of(commit.get("committer", ""))) if p}
    if not people:
        return []
    out: list[str] = []
    for m in TRAILER_RE.finditer(commit.get("message", "")):
        who = m.group("who")
        person = person_of(who)
        if person and person["name"] in people:
            out.append(f"{m.group('key')}: {who}")
    return out


def spelling_violations(commit: dict) -> list[str]:
    """Author/committer identities that are a NON-CANONICAL spelling of a known person (#445).

    The allowlist answers "may this identity be credited?"; it never answered "is this one
    person using several". A second spelling is what makes the merge synthesize the duplicate
    trailer, so the guard names the canonical pair instead of only refusing the value.
    """
    out: list[str] = []
    for role in ("author", "committer"):
        ident = commit.get(role, "")
        canonical = canonical_for(ident)
        if canonical:
            out.append(f"{role} identity {ident} is a second spelling of that person — use {canonical}")
    return out


def scan(commits: list[dict]) -> list[str]:
    """The violations in a list of `{sha, author, committer, subject, message}`."""
    bad: list[str] = []
    for c in commits:
        sha = c["sha"][:12]
        for role in ("author", "committer"):
            ident = c.get(role, "")
            if not ident_allowed_any(ident):
                bad.append(
                    f"{sha}: {role} identity not allowed: {ident} "
                    f"(subject: {c.get('subject', '')})"
                )
        for trailer in trailer_violations(c.get("message", "")):
            bad.append(
                f"{sha}: commit message credits a disallowed co-author: {trailer} "
                f"(subject: {c.get('subject', '')})"
            )
        # ONE PERSON, ONE IDENTITY (issue #445): the same person twice in one message, and the
        # non-canonical spelling that makes GitHub write that duplicate in the first place.
        for trailer in self_credit_violations(c):
            bad.append(
                f"{sha}: the commit credits ITS OWN author a second time: {trailer} "
                f"(one person, one identity — {c.get('subject', '')})"
            )
        for problem in spelling_violations(c):
            bad.append(f"{sha}: {problem} (subject: {c.get('subject', '')})")
    return bad


def ident_allowed_any(ident: str) -> bool:
    return identity_allowed(ident)


def collect(root: Path, rev_range: str) -> list[dict]:
    """Read the commits in `rev_range` — or raise `GuardUnavailable`."""
    fmt = "%x00".join(["%H", "%an <%ae>", "%cn <%ce>", "%s", "%B"]) + "%x00%x00"
    try:
        out = subprocess.run(
            ["git", "log", f"--format={fmt}", rev_range],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # git itself is missing
        raise GuardUnavailable(f"could not run git: {exc}") from exc

    if out.returncode != 0:
        raise GuardUnavailable(
            f"`git log {rev_range}` failed in {root}:\n{out.stderr.strip()}\n"
            "  A range that cannot be read is a defect, not a pass. If this is a\n"
            "  shallow clone (the CI checkout defaults to `fetch-depth: 1`), the\n"
            "  base ref is simply not here — the checkout that runs this guard must\n"
            "  use `fetch-depth: 0` (issue #317), or pass an explicit --range."
        )

    commits: list[dict] = []
    for chunk in out.stdout.split("\x00\x00"):
        chunk = chunk.strip("\x00\n")
        if not chunk:
            continue
        parts = chunk.split("\x00")
        if len(parts) < 5:
            continue
        sha, author, committer, subject, message = parts[0], parts[1], parts[2], parts[3], parts[4]
        commits.append(
            {
                "sha": sha,
                "author": author,
                "committer": committer,
                "subject": subject,
                "message": message,
            }
        )
    return commits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("check", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=".", help="the repository to read")
        p.add_argument("--range", dest="rev_range", default=DEFAULT_RANGE)
        p.add_argument(
            "--message-file",
            action="append",
            default=[],
            help="scan this file as a commit message instead of git (repeatable)",
        )
        p.add_argument(
            "--identity",
            action="append",
            default=[],
            help="check this `Name <email>` identity instead of git (repeatable)",
        )

    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.message_file or args.identity:
        commits = []
        for f in args.message_file:
            text = Path(f).read_text(encoding="utf-8", errors="replace")
            subject = text.splitlines()[0] if text.strip() else ""
            commits.append(
                {"sha": "offline", "author": "", "committer": "", "subject": subject, "message": text}
            )
        for ident in args.identity:
            commits.append(
                {"sha": "offline", "author": ident, "committer": ident, "subject": "", "message": ""}
            )
    else:
        try:
            commits = collect(root, args.rev_range)
        except GuardUnavailable as exc:
            print(f"[commit-authorship] FAIL {exc}", file=sys.stderr)
            return 2

    bad = scan(commits)

    if args.cmd == "report":
        print(f"[commit-authorship] range={args.rev_range} commits={len(commits)}")
        for c in commits:
            print(f"  {c['sha'][:12]}  {c['author']}  |  {c['subject']}")
        if bad:
            print(f"[commit-authorship] {len(bad)} violation(s):")
            for v in bad:
                print(f"  {v}")
        else:
            print("[commit-authorship] no violations.")
        return 0

    if bad:
        print(
            "[commit-authorship] FAIL the only identities on this repo are Andy Holst and "
            "Asimov Agent (issue #317).",
            file=sys.stderr,
        )
        for v in bad:
            print(f"  {v}", file=sys.stderr)
        print(
            "  A `Co-authored-by:` trailer naming anyone else is refused, and so is a\n"
            "  commit AUTHORED or COMMITTED as anyone else — GitHub synthesizes the\n"
            "  trailer from the author identity at squash time, so the message alone\n"
            "  does not prove the identity. Set `git config user.name`/`user.email`\n"
            "  (or GIT_AUTHOR_*/GIT_COMMITTER_*) to an allowed identity and amend.",
            file=sys.stderr,
        )
        return 1

    print(
        f"[commit-authorship] OK {len(commits)} commit(s) in {args.rev_range} "
        "carry only allowed identities and no disallowed co-author trailer."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
