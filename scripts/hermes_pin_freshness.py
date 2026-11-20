#!/usr/bin/env python3
"""hermes-pin-freshness — the pinned Hermes agent version vs the upstream release channel.

Issue #1091, rule 6k. The Makefile's ``HERMES_VERSION ?=`` and the Dockerfile's
``ARG HERMES_VERSION="…"`` pin the agent version every fleet image bakes (issue #218
pins the two together); this reads BOTH back — a silent disagreement between them is
itself the #218 defect, so the check REFUSES (exit 2) before comparing anything — and
compares the pin against the upstream release channel. The channel repo is DERIVED
from the Makefile's install-pin block (issue #1094, rule 6d): the single
``HERMES_CHANNEL_REPO ?=`` line beside ``HERMES_INSTALL_URL`` is the ONLY spelling in
this repository, read through the same seam as the pins (``gh api
repos/<channel>/releases/latest``), and a Makefile without it is a loud refusal —
never a fallback literal baked into this script:

  equal           -> prints ``pin=<v> channel=<v> OK``, exit 0
  channel newer   -> exit 1 (loud: the queued-alarm sweep goes red) and files ONE
                     marker-deduplicated ``tech-debt`` issue naming the remedy —
                     raise BOTH pins together per issue #218
  pin ahead       -> reported (``AHEAD``), exit 0 — a reported state, not a red one
  channel unreadable -> exit 2, never a silent clean

The channel is compared through the real recorded payload: a live ``gh api`` on the
host, or ``--from-file`` with a recorded payload (the ``check_branch_protection.py``
FROM_FILE seam, issue #959) — no version-parsing mocks. The dedup marker lives in
``scripts/bot_markers.py`` (rule 6j); this module imports it and never re-spells it.

Issue #1163: the SAME read is also the ONE way the recorded fixture is REFRESHED. The
fixture ``tests/fixtures/hermes_releases_latest.json`` is what ``make test``'s offline
half asserts against, and until now nothing wrote it — a pin raise had to hand-copy
``gh api …/releases/latest`` into the fixture, the step that silently goes stale. The
``--record PATH`` mode writes the payload this seam READS (never an authored one),
refuses loudly (exit 2, the old file untouched) when gh or the network fails, and is
wired into the refresh pipeline beside ``make engine-meta-capture`` (issue #334's
recorder), which commits it into the refresh PR.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bot_markers  # noqa: E402  (rule 6j: the marker shape lives there, never re-spelled here)

#: The upgrade rule the filed issue names: an upgrade raises BOTH pins together.
UPGRADE_ISSUE = 218

#: The channel repo has ONE spelling — the Makefile's install-pin block (issue
#: #1094, rule 6d). This module NEVER bakes a channel literal; it reads the pin.
CHANNEL_PIN_NAME = "HERMES_CHANNEL_REPO"

#: The pin-drift dedup signature lives in scripts/bot_markers.py (rule 6j); this module
#: renders it THROUGH the registered name and never re-spells it.
PIN_DRIFT_KEY = bot_markers.PIN_DRIFT_SIGNATURE_KEY

_LABEL = "tech-debt"

_TAG = re.compile(r"^v?(\d+(?:\.\d+)*)(?:[-+].*)?$")
_MAKE_PIN = re.compile(r"^\s*HERMES_VERSION\s*\?=\s*([^\s#]+)", re.M)
_DOCKER_PIN = re.compile(r'^\s*ARG\s+HERMES_VERSION\s*=?\s*"?([^\s"#]+)"?', re.M)
_MAKE_CHANNEL = re.compile(r"^\s*HERMES_CHANNEL_REPO\s*\?=\s*([^\s#]+)", re.M)


class PinMismatch(Exception):
    """The Makefile and the Dockerfile name DIFFERENT agent versions (rule 6k)."""


class ChannelUnreadable(Exception):
    """The upstream channel tag could not be read — reported loudly, never silently clean."""


class VersionError(Exception):
    """A pin or a channel tag is not a version this check can honestly order."""


def version_tuple(text: str) -> tuple[int, ...]:
    m = _TAG.match(str(text).strip())
    if not m:
        raise VersionError(f"not a version this check can order: {text!r}")
    return tuple(int(p) for p in m.group(1).split("."))


def compare(left: str, right: str) -> int:
    """-1 when left < right, 0 equal, 1 when left > right (zero-padded tuples)."""
    a, b = version_tuple(left), version_tuple(right)
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return (a > b) - (a < b)


def _first_pin(text: str, pattern: re.Pattern, spelling: str) -> tuple[str, int]:
    """(value, 1-based line) of the first pin this pattern finds."""
    m = pattern.search(text)
    if not m:
        raise PinMismatch(f"{spelling} carries no version pin the check can read")
    line = text[: m.start()].count("\n") + 1
    return m.group(1), line


def read_pins(makefile: Path, dockerfile: Path) -> tuple[str, int, str, int]:
    """(makefile_pin, makefile_line, dockerfile_pin, dockerfile_line) — rule 6k pins
    them together, so a disagreement is refused BEFORE the channel is even consulted."""
    try:
        mk_text = makefile.read_text(encoding="utf-8")
        df_text = dockerfile.read_text(encoding="utf-8")
    except OSError as exc:
        raise PinMismatch(f"cannot read the pin files: {exc}") from exc
    mk_pin, mk_line = _first_pin(mk_text, _MAKE_PIN, f"{makefile.name}")
    df_pin, df_line = _first_pin(df_text, _DOCKER_PIN, f"{dockerfile.name}")
    if version_tuple(mk_pin) != version_tuple(df_pin):
        raise PinMismatch(
            f"the pins disagree: {makefile.name}:{mk_line} `HERMES_VERSION ?= {mk_pin}` vs "
            f"{dockerfile.name}:{df_line} `ARG HERMES_VERSION=\"{df_pin}\"` — rule 6k "
            f"(issue #{UPGRADE_ISSUE}) pins the two together; raise or lower BOTH in one change"
        )
    return mk_pin, mk_line, df_pin, df_line


def read_channel_repo(makefile: Path) -> str:
    """The channel repo DERIVED from the Makefile's install-pin block (issue #1094,
    rule 6d): the single ``HERMES_CHANNEL_REPO ?=`` line beside ``HERMES_INSTALL_URL``
    is the ONLY spelling in this repository. A Makefile without it is a loud refusal
    naming the pin — never a fallback to a channel literal baked into this script."""
    try:
        text = makefile.read_text(encoding="utf-8")
    except OSError as exc:
        raise ChannelUnreadable(f"cannot read the channel pin in {makefile}: {exc}") from exc
    m = _MAKE_CHANNEL.search(text)
    if not m:
        raise ChannelUnreadable(
            f"{makefile.name} carries no `{CHANNEL_PIN_NAME} ?=` pin — the upstream release "
            f"channel has no home to read it from (issue #1094: the channel's ONE spelling is "
            f"the Makefile install-pin block)")
    return m.group(1)


def read_channel(from_file: str | None, channel_repo: str) -> tuple[dict, str]:
    """(payload, raw text) of the upstream release — the ONE read (issue #1163).

    ``channel_repo`` is derived from the Makefile pin (``read_channel_repo``).
    ``from_file`` names a recorded payload (the FROM_FILE seam); without it this runs
    ``gh api repos/<channel_repo>/releases/latest``. Any failure — gh missing, network,
    a payload that is not a JSON object — is UNREADABLE (exit 2), never "fresh". The
    raw text is returned beside the parsed payload so ``--record`` can write EXACTLY
    what the channel served, never a re-authored document.
    """
    if from_file:
        try:
            text = Path(from_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise ChannelUnreadable(f"recorded channel payload {from_file!r} unreadable: {exc}") from exc
    else:
        proc = subprocess.run(["gh", "api", f"repos/{channel_repo}/releases/latest"],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise ChannelUnreadable(
                f"`gh api repos/{channel_repo}/releases/latest` failed "
                f"(rc={proc.returncode}): {proc.stderr.strip()[:300] or 'no stderr'}")
        text = proc.stdout
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ChannelUnreadable(f"the channel payload is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ChannelUnreadable("the channel payload is not a JSON object")
    return payload, text


def channel_tag(from_file: str | None, channel_repo: str) -> str:
    """The upstream channel's release tag, read from the REAL payload.

    ``channel_repo`` is derived from the Makefile pin (``read_channel_repo``).
    ``from_file`` names a recorded payload (the FROM_FILE seam); without it this runs
    ``gh api repos/<channel_repo>/releases/latest`` and treats any failure —
    gh missing, network, a payload with no ``tag_name`` — as UNREADABLE (exit 2), never
    as "fresh".
    """
    payload, _text = read_channel(from_file, channel_repo)
    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        raise ChannelUnreadable("the channel payload carries no `tag_name`")
    try:
        version_tuple(tag)
    except VersionError as exc:
        raise ChannelUnreadable(f"the channel tag {tag!r} is not a version: {exc}") from exc
    return tag


def record_channel_payload(path: Path, from_file: str | None,
                           channel_repo: str) -> tuple[str, str]:
    """Write the channel payload to ``path`` through the ONE seam (issue #1163).

    Returns ``(tag, published_at)``. The bytes written are the payload the seam READ
    (the live ``gh api`` stdout, or the recorded file's own text) — never an authored
    document — so a refresh that changes nothing rewrites nothing. A failed read raises
    BEFORE any write, so the old fixture stays byte-identical.
    """
    payload, text = read_channel(from_file, channel_repo)
    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        raise ChannelUnreadable("the channel payload carries no `tag_name`")
    try:
        version_tuple(tag)
    except VersionError as exc:
        raise ChannelUnreadable(f"the channel tag {tag!r} is not a version: {exc}") from exc
    published = str(payload.get("published_at") or "").strip()
    if not published:
        raise ChannelUnreadable("the channel payload carries no `published_at`")
    body = text if text.endswith("\n") else text + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)
    return tag, published


def drift_signature(channel: str) -> str:
    """ONE signature per drifted channel version (channel-keyed: the same drift the
    sweep sees twice is one tracked issue; a closed issue does not block a fresh drift)."""
    return "hermes-pin-" + ".".join(str(p) for p in version_tuple(channel))


def already_filed(repo: str, signature: str) -> str | None:
    """The URL of an OPEN issue already carrying this drift signature, or None."""
    proc = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "all", "--label", _LABEL,
         "--search", f'"{signature}" in:body', "--json", "number,state,url"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[hermes-pin-freshness] gh issue list failed (rc={proc.returncode}): "
                         f"{proc.stderr.strip()[:300]}")
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return None
    for item in items:
        if item.get("state") == "OPEN":
            return str(item.get("url") or item.get("number"))
    return None


def issue_body(repo: str, pin: str, mk_line: int, df_line: int, channel: str,
               channel_repo: str) -> str:
    signature = drift_signature(channel)
    utc = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return (
        "## Finding\n\n"
        f"- **Evidence:** `Makefile:{mk_line}` pins `HERMES_VERSION ?= {pin}` and "
        f"`Dockerfile:{df_line}` pins `ARG HERMES_VERSION=\"{pin}\"` — the agent version every "
        f"fleet image bakes (issue #{UPGRADE_ISSUE}, rule 6k); `repos/{channel_repo}/releases/latest` "
        f"answers tag `{channel}` — the upstream stable channel is strictly NEWER than the pin. "
        f"Compared by `make hermes-pin-freshness REPO={repo}`.\n"
        f"- **Why:** a pinned build is reproducible but silently ages: every image keeps baking "
        f"`{pin}` while the upstream channel moved to `{channel}`, and the drift only surfaces at "
        f"the next image dispatch/build (rule 6k) — today it has no tracked home until the sweep "
        f"names it.\n"
        f"- **Done when:** raise the Makefile's `HERMES_VERSION` and the Dockerfile's "
        f"`ARG HERMES_VERSION` together per issue #{UPGRADE_ISSUE} (an explicit, reviewable "
        f"upgrade — never one pin alone), and `make hermes-pin-freshness REPO={repo}` prints "
        f"`pin=<v> channel=<v> OK` and exits 0.\n\n"
        "## Origin\n\n"
        f"Filed by `make hermes-pin-freshness` on {utc}.\n\n"
        f"<!-- {PIN_DRIFT_KEY}: {signature} -->\n"
    )


def file_drift_issue(repo: str, pin: str, mk_line: int, df_line: int, channel: str,
                     channel_repo: str) -> tuple[str, str]:
    """('filed'|'already-filed', url) — ONE issue per drifted channel version, marker-deduped."""
    signature = drift_signature(channel)
    existing = already_filed(repo, signature)
    if existing:
        return "already-filed", existing
    title = (f"tech-debt: Hermes agent pin {pin} lags the upstream release channel {channel} "
             f"(make hermes-pin-freshness)")
    proc = subprocess.run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--label", _LABEL,
         "--body", issue_body(repo, pin, mk_line, df_line, channel, channel_repo)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[hermes-pin-freshness] gh issue create failed (rc={proc.returncode}): "
                         f"{proc.stderr.strip()[:300]}")
    url = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "?"
    return "filed", url


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", help="owner/name — the repo the drift issue is filed on "
                                   "(required unless --record is given)")
    ap.add_argument("--from-file", help="a recorded channel payload (the FROM_FILE seam) instead of `gh api`")
    ap.add_argument("--record", metavar="PATH",
                    help="write the channel payload to PATH through the ONE seam (issue #1163) — "
                         "the refresh fixture's recorder; never writes an authored document")
    ap.add_argument("--channel-repo", help="the release channel repo the recipe passes from the "
                                           "Makefile's `HERMES_CHANNEL_REPO ?=` knob; without it "
                                           "the same line is read from --makefile (issue #1094)")
    ap.add_argument("--makefile", default=str(ROOT / "Makefile"), help=argparse.SUPPRESS)
    ap.add_argument("--dockerfile", default=str(ROOT / "Dockerfile"), help=argparse.SUPPRESS)
    ap.add_argument("--dry-run", action="store_true", help="report the drift without filing")
    args = ap.parse_args(argv)

    if args.record:
        # The recorder needs the channel pin, never the drift issue's repo (issue #1163).
        try:
            channel_repo = args.channel_repo or read_channel_repo(Path(args.makefile))
        except ChannelUnreadable as exc:
            print(f"[hermes-pin-channel-record] FAIL — the channel pin is missing: {exc}",
                  file=sys.stderr)
            return 2
        try:
            tag, published = record_channel_payload(Path(args.record), args.from_file, channel_repo)
        except ChannelUnreadable as exc:
            print(f"[hermes-pin-channel-record] FAIL — the channel payload could not be read: {exc}"
                  f" (nothing written; {args.record} is untouched)", file=sys.stderr)
            return 2
        print(f"[hermes-pin-channel-record] wrote {args.record} tag={tag} published_at={published}")
        return 0

    if not args.repo:
        print("[hermes-pin-freshness] --repo is required unless --record PATH is given",
              file=sys.stderr)
        return 2
    if "/" not in args.repo or args.repo.count("/") != 1:
        print("[hermes-pin-freshness] --repo must be owner/name", file=sys.stderr)
        return 2

    try:
        pin, mk_line, _df_pin, df_line = read_pins(Path(args.makefile), Path(args.dockerfile))
    except PinMismatch as exc:
        print(f"[hermes-pin-freshness] FAIL — {exc}", file=sys.stderr)
        return 2
    except VersionError as exc:
        print(f"[hermes-pin-freshness] FAIL — the pin is unreadable: {exc}", file=sys.stderr)
        return 2

    try:
        # The channel repo has ONE spelling: the Makefile install-pin block (issue #1094).
        # The recipe forwards the expanded knob via --channel-repo; a direct invocation
        # reads the SAME `HERMES_CHANNEL_REPO ?=` line from --makefile. Either way the
        # script never consults a channel literal it baked.
        channel_repo = args.channel_repo or read_channel_repo(Path(args.makefile))
    except ChannelUnreadable as exc:
        print(f"[hermes-pin-freshness] FAIL — the channel pin is missing: {exc}",
              file=sys.stderr)
        return 2

    try:
        channel = channel_tag(args.from_file, channel_repo)
    except ChannelUnreadable as exc:
        print(f"[hermes-pin-freshness] FAIL — the upstream channel could not be read: {exc}",
              file=sys.stderr)
        return 2

    order = compare(pin, channel)
    if order == 0:
        print(f"pin={pin} channel={channel} OK")
        return 0
    if order > 0:
        print(f"pin={pin} channel={channel} AHEAD — the pin is ahead of the upstream channel "
              f"(reported, not red)")
        return 0

    print(f"pin={pin} channel={channel} DRIFT — the upstream release channel is strictly newer "
          f"than the pinned agent version")
    if args.dry_run:
        print("[hermes-pin-freshness] --dry-run: filing skipped")
        return 1
    try:
        verdict, url = file_drift_issue(args.repo, pin, mk_line, df_line, channel, channel_repo)
    except SystemExit as exc:
        print(f"[hermes-pin-freshness] FAIL — the drift issue could not be filed: {exc}", file=sys.stderr)
        return 2
    print(f"[hermes-pin-freshness] {verdict}={url}")
    print(f"[hermes-pin-freshness] remedy: raise the Makefile `HERMES_VERSION` and the Dockerfile "
          f"`ARG HERMES_VERSION` together per issue #{UPGRADE_ISSUE} (rule 6k)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
