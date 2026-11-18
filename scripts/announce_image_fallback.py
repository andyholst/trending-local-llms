#!/usr/bin/env python3
"""Announce on the PR which runner images CI built WITHOUT a pull (issue #1120).

The corrupt-tag fallback (issue #1118) is green either way: when ghcr serves a
published hash tag's manifest but not its blobs, `scripts/ensure_image.py`
builds THIS revision's image locally and the PR stays green. That supply-chain
distinction lived only in one job's log. This is the PR-facing half: the seam
prints `corrupt-tag-fallback=<image>=<tag>` lines, the qa-validate `validate`
job captures them into an allowlisted `GITHUB_OUTPUT` key (rule 3f) and calls
`make announce-image-fallback`, and THIS script posts ONE marker-deduplicated
comment naming exactly which images were built without a pull.

Rule 6j: the marker is `bot_markers`'s registered `qa-validate/image_fallback`
(`corrupt-tag-fallback`), stamped `run=<run-id>` — the stamp dates it, the run
id dedups it (one CI run announces once; a re-run with a new id may announce
again). The comment read is `--paginate` across every page (the #662 class: a
first-page read misses the newest comment and double-posts).

Post goes through `gh issue comment` with the ambient default `github.token`
(the owner PAT cannot comment — rule 6e). A missing PR number, repo or images
list is a loud exit 2, never a silent pass.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_markers as bm  # noqa: E402

BOT, KIND = "qa-validate", "image_fallback"


class GhError(RuntimeError):
    pass


def _gh(args: list[str]) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GhError(f"gh {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def read_comments(repo: str, pr: str) -> list[dict]:
    """Every comment on the PR's thread, across EVERY page (issue #662).

    GitHub returns comments oldest-first; the marker this dedup hunts for is the
    NEWEST one — a first-page-only read would miss it and double-post. Same
    reader shape as scripts/sweep_outcome.py's thread read.
    """
    out = _gh(["api", f"repos/{repo}/issues/{pr}/comments", "--paginate", "--jq", ".[]"])
    comments: list[dict] = []
    try:
        for line in out.splitlines():
            if line.strip():
                comments.append(json.loads(line))
    except json.JSONDecodeError as exc:
        raise GhError(f"could not read PR #{pr}'s comments: {exc}") from None
    return comments


def already_announced(comments: list[dict], run_id: str) -> bool:
    """This CI run already announced — the marker's `run=<id>` is the dedup key.

    A stamp of a DIFFERENT run does not suppress: a fresh run may announce again.
    """
    for comment in comments:
        body = comment.get("body") or ""
        if bm.read_marker(body, BOT, KIND) and f"run={run_id}" in body:
            return True
    return False


def parse_images(values: str) -> list[tuple[str, str]]:
    """`corrupt-tag-fallback=base=<tag> …` -> [(base, tag), …] — the seam's own lines.

    The seam prints/records each fallback as the registered machine line
    `corrupt-tag-fallback=<image>=<tag>`; the step joins those lines into ONE
    space-separated GITHUB_OUTPUT value, so a token may carry the marker-name
    prefix (the real shape) or the bare `<image>=<tag>` (a hand-typed list).
    """
    pairs: list[tuple[str, str]] = []
    for token in values.split():
        token = token.removeprefix(f"{bm.marker_name(BOT, KIND)}=")
        name, sep, tag = token.partition("=")
        if not sep or not name or not tag:
            raise ValueError(f"bad image report '{token}' (want <image>=<tag>)")
        pairs.append((name, tag))
    return pairs


def compose_comment(images: list[tuple[str, str]], run_url: str, when: dt.datetime,
                    run_id: str) -> str:
    marker = bm.start_marker(BOT, when, run=run_id, kind=KIND)
    lines = [
        "## Corrupt-tag fallback: CI built a runner image without a pull",
        "",
        "A published runner-image tag was in the registry but its blobs were not "
        "fetchable (the ghcr blob-GC state issue #1118 names). `make image-ensure` / "
        "`make openspec-check` fell back to building THIS revision's Dockerfile "
        "locally, so the PR validated against a locally built image rather than the "
        "published, content-hashed artifact. This is a green path (#1118 made it "
        "deliberate) — the comment exists so the distinction is visible on the PR, "
        "not only in one job's log.",
        "",
    ]
    for name, tag in images:
        lines.append(f"- `{name}`: tag `{tag}` — published, blobs unfetchable; built from this revision's Dockerfile")
    if run_url:
        lines.append("")
        lines.append(f"Run: {run_url}")
    lines.append("")
    lines.append(marker)
    return "\n".join(lines) + "\n"


def post_comment(repo: str, pr: str, body: str) -> None:
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w") as fh:
        fh.write(body)
    try:
        _gh(["issue", "comment", str(pr), "--repo", repo, "--body-file", path])
    finally:
        os.unlink(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Post ONE comment on the PR naming which runner images the corrupt-tag "
                    "fallback built without a pull (issue #1120)")
    ap.add_argument("--repo", default=os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY"))
    ap.add_argument("--pr", default=os.environ.get("PR_NUMBER") or os.environ.get("PR"))
    ap.add_argument("--images", default=os.environ.get("IMAGES") or "",
                    help="space-separated <image>=<tag> pairs (what the seam printed)")
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    ap.add_argument("--run-url", default=os.environ.get("RUN_URL") or os.environ.get("GITHUB_SERVER_URL", "")
                    + "/" + os.environ.get("GITHUB_REPOSITORY", "") + "/actions/runs/"
                    + os.environ.get("GITHUB_RUN_ID", ""))
    ap.add_argument("--now", default=None, help="Iso8601 instant for the marker (tests)")
    ap.add_argument("--post", action="store_true", help="write the comment (default: print it)")
    args = ap.parse_args(argv)

    repo = (args.repo or "").strip()
    pr = (args.pr or "").strip().lstrip("#")
    if not repo:
        print("[announce-image-fallback] FAIL: no repo (--repo / GITHUB_REPOSITORY)", file=sys.stderr)
        return 2
    if not pr or not pr.isdigit():
        print(f"[announce-image-fallback] FAIL: '{args.pr}' is not a PR number", file=sys.stderr)
        return 2
    if not args.images.strip():
        print("[announce-image-fallback] FAIL: no images to announce — the seam reported no "
              "corrupt-tag fallback (--images / IMAGES)", file=sys.stderr)
        return 2
    run_id = (args.run_id or "").strip()
    if not run_id:
        print("[announce-image-fallback] FAIL: no run id to stamp the announcement with "
              "(--run-id / GITHUB_RUN_ID)", file=sys.stderr)
        return 2
    try:
        images = parse_images(args.images)
    except ValueError as exc:
        print(f"[announce-image-fallback] FAIL: {exc}", file=sys.stderr)
        return 2

    when = (dt.datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now
            else dt.datetime.now(dt.timezone.utc))

    try:
        comments = read_comments(repo, pr)
    except GhError as exc:
        print(f"[announce-image-fallback] FAIL: {exc}", file=sys.stderr)
        return 2
    if already_announced(comments, run_id):
        print(f"[announce-image-fallback] deduped: run {run_id} already announced on PR #{pr}; "
              "no comment posted")
        return 0

    body = compose_comment(images, args.run_url, when, run_id)
    if not args.post:
        print(body)
        print("[announce-image-fallback] dry run (no --post): nothing written")
        return 0
    try:
        post_comment(repo, pr, body)
    except GhError as exc:
        print(f"[announce-image-fallback] FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"[announce-image-fallback] announced {len(images)} image(s) on PR #{pr} "
          f"(run {run_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
