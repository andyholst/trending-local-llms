#!/usr/bin/env python3
"""The file set of `make secret-scan` is what git could commit (issue #836).

gitleaks `dir` mode walks every checked-out file and never consults `.gitignore`
(measured: after a local `make test`, the pre-push gate went red on six findings
in `tests/__pycache__/*.cpython-312.pyc` — compiled copies of the self-test's own
planted FAKE credentials). Those bytes can never be committed: git itself will
not stage them. This script is the ONE decision (rule 6d): it classifies every
gitleaks finding with `git check-ignore` — git's own gitignore semantics, never
a hand-maintained path list — and fails the gate only on findings in files git
could commit.

  python3 scripts/secret_scan_report.py --report .secret-scan-report.json \
      [--repo .] [--mount /repo/]

  exit 0  no committable finding (gitignored artifacts are REPORTED, not hidden)
  exit 1  a finding lives in a committable file — the pre-push gate stays red
  exit 2  the scan input is broken (no/unreadable report, or git refused) — a
          silent "clean" over an unreadable scan is the defect this refuses

Stdlib only, host-side like `make lint`. Never prints a secret value: only the
file, the line and the rule id (gitleaks runs `--redact`; that is treated as
belt-and-braces, never relied on).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_LEAK = 1
EXIT_BROKEN = 2


def load_findings(report: Path) -> list[dict]:
    """The gitleaks JSON report, loudly refused when the scan wrote nothing."""
    if not report.is_file():
        print(f"[secret-scan] BROKEN: the scan wrote no report at {report} — "
              "a scanner that writes nothing is a false green, not a clean tree")
        raise SystemExit(EXIT_BROKEN)
    try:
        findings = json.loads(report.read_text() or "[]")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[secret-scan] BROKEN: cannot read the scan report {report}: {exc}")
        raise SystemExit(EXIT_BROKEN) from exc
    if not isinstance(findings, list):
        print(f"[secret-scan] BROKEN: {report} is not a gitleaks findings list")
        raise SystemExit(EXIT_BROKEN)
    return findings


def repo_relative(file_value: str, mount: str) -> str:
    """Map a report path to a repo-relative one.

    `dir` mode reports the CONTAINER path (under `--mount`, e.g.
    /repo/tests/__pycache__/x.pyc). A path NOT under the mount that is still
    absolute (a scan reached something outside the repo) is kept ABSOLUTE:
    `git check-ignore` refuses absolute paths, and an out-of-repo file is not
    git's to excuse — it stays in the committable-class side (fail-safe:
    unknown never means ignored)."""
    if file_value.startswith(mount):
        return file_value[len(mount):]
    return file_value


def ignored_by_git(repo: Path, paths: list[str]) -> set[str]:
    """git's own answer, one call: which of these paths could git commit?

    `git check-ignore` matches the .gitignore chain (and prints NUL-separated
    matches). A path git refuses to match is committable — including a tracked
    file a rogue `git add -f` forced in: check-ignore answers only for
    uncommitted candidates, so a committed artifact stays BLOCKING."""
    if not paths:
        return set()
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "--stdin", "-z"],
            cwd=repo, input="\0".join(paths).encode(),
            capture_output=True,
        )
    except OSError as exc:  # git not reachable — refuse, never guess
        print(f"[secret-scan] BROKEN: `git check-ignore` could not run: {exc}")
        raise SystemExit(EXIT_BROKEN) from exc
    if proc.returncode == 128:
        print(f"[secret-scan] BROKEN: git check-ignore failed in {repo}: "
              f"{proc.stderr.decode(errors='replace').strip()}")
        raise SystemExit(EXIT_BROKEN)
    # rc 0 = at least one ignored, rc 1 = none ignored; anything else is broken.
    if proc.returncode not in (0, 1):
        print(f"[secret-scan] BROKEN: git check-ignore exited {proc.returncode}")
        raise SystemExit(EXIT_BROKEN)
    return {p for p in proc.stdout.decode(errors="replace").split("\0") if p}


def main() -> int:
    ap = argparse.ArgumentParser(description="The secret-scan fileset verdict (issue #836)")
    ap.add_argument("--report", required=True,
                    help="the gitleaks JSON report `make secret-scan` wrote")
    ap.add_argument("--repo", default=".",
                    help="the git repository the scan ran against (default: cwd)")
    ap.add_argument("--mount", default="/repo/",
                    help="the container mount prefix dir-mode paths carry (default /repo/)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    findings = load_findings(Path(args.report))
    if not findings:
        print("[secret-scan] clean: no findings in the checked-out tree")
        return EXIT_OK

    mount = args.mount if args.mount.endswith("/") else args.mount + "/"
    rows = []
    for finding in findings:
        file_value = str(finding.get("File") or finding.get("Path") or "")
        line = finding.get("StartLine") or (finding.get("LineInfo") or [None])[0] or "?"
        rule = str(finding.get("RuleID") or finding.get("Rule") or "?")
        rows.append((repo_relative(file_value or "<unknown>", mount), line, rule))

    unique = sorted({path for path, _, _ in rows if not path.startswith("/")})
    ignored = ignored_by_git(repo, unique)

    # An absolute (out-of-repo) path is never git's to excuse: check-ignore
    # cannot answer for it, and unknown never means ignored.
    blocking = [r for r in rows if r[0].startswith("/") or r[0] not in ignored]
    artifacts = [r for r in rows if not r[0].startswith("/") and r[0] in ignored]

    print(f"[secret-scan] {len(rows)} finding(s): "
          f"{len(blocking)} committable, {len(artifacts)} gitignored artifact(s)")
    for path, line, rule in blocking:
        print(f"  BLOCKING {path}:{line}  rule={rule}")
    for path, line, rule in sorted(set(artifacts)):
        print(f"  ignored  {path}:{line}  rule={rule}  "
              "(gitignored build artifact — can never be committed)")

    if blocking:
        print("[secret-scan] FAIL: a credential shape sits in a file git could commit. "
              "Remove the value, rotate the key, and never allowlist a real value.")
        return EXIT_LEAK
    print("[secret-scan] OK: nothing a commit could carry. The gitignored artifacts "
          "above are reported, not hidden — delete the caches if you want them gone.")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
