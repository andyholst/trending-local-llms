#!/usr/bin/env python3
"""Fail when a PUBLIC make target reaches a bare HOST `python3` / `pip` / `uv` (issue #712 Slice 5).

`#712` makes `make` OS-agnostic: every command runs inside one of the repo's Linux images through
a seam (`PYTHON_RUN` for the python-env image, `TEST_RUN`/`DOCKER_RUN` for the test/base images,
`OS_OPTS` for the OpenSpec CLI). A recipe that calls the host interpreter directly defeats that —
the runner's Python becomes part of the pipeline.

This guard is the mechanical half of the rule. It reads the REAL Makefile (never a copy) and asks
of every public target: does a recipe line, or one make hop into a PRIVATE `_x` recipe, invoke
`python3`/`pip`/`uv` with NO container harness on that line? A target that does is reported UNLESS
it is one of the DELIBERATE host-only seams in `EXCEPTIONS` below — image build/selection, gh/GitHub-state
verifiers, host git identity/worktree, and the cheapest pre-image-ensure guards. That list is the
ONE machine-readable exception list; the Makefile comment block above the `PYTHON_RUN` seam
carries the same names between `# HOST-EXCEPTIONS-BEGIN/END`, and `tests/test_os_agnostic_make.py`
proves the two agree, so a new bare invocation cannot land silently and a removed one cannot
linger as dead documentation.

The token set also names the pip-tools console scripts as their OWN words — `pip-compile`,
`pip-sync`, `pip-tools`. They are matched BEFORE the bare `pip` spelling (#1593): with only
`pip` in the alternation the trailing `-` lookahead rejected `pip-compile`, so a planted
`pip-compile …` in a non-exception public target exited 0 INVISIBLE while the guard's own docstring
promised to name it.

What it deliberately does NOT do: it does not judge `bash`/`git`/`gh`/`docker`/`hermes` (those are
host tools the container seams themselves need), and it does not run anything — a bare reading of
the tree, so it is cheap enough to sit inside `make lint`.

Usage:
    python3 scripts/check_no_bare_host_python.py                 # gate (exit 0/1/2)
    python3 scripts/check_no_bare_host_python.py --list-exceptions
    python3 scripts/check_no_bare_host_python.py --root <repo root>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import architecture_bot  # noqa: E402  (the ONE Makefile target-line parser — rule 6d, issue #752)

#: The container seams. A line carrying one of these is NOT a bare host invocation.
HARNESS_TOKENS = ("$(PYTHON_RUN)", "$(TEST_RUN)", "$(DOCKER_RUN)", "$(OS_OPTS)", "docker run")

#: A host interpreter invocation, but not `python3.12` / `my-python3` / `scripts/pip`.
#: The pip-tools console scripts are their OWN words — `pip-compile`, `pip-sync`,
#: `pip-tools` — so they come FIRST in the alternation: a shorter alternative earlier
#: would match only the `pip` prefix and the trailing `-` lookahead would then reject it,
#: which is exactly the hole #1593 measured (a planted `pip-compile …` exited 0).
INTERP_RE = re.compile(
    r"(?<![\w.$/@-])(pip-compile|pip-sync|pip-tools|python3|pip|uv)(?![\w.-])")

#: Split a recipe line into pipeline/list segments so `cmd | $(PYTHON_RUN) python3 x` is clean
#: while `cmd | python3 x` is not.
SEGMENT_SPLIT = re.compile(r"\|+|&&|\|\||;|&")

#: A hop into a PRIVATE recipe, in BOTH spellings the Makefile uses (#1596): `$(MAKE) … _x` and the
#: repo's own dominant idiom, the plain `make _x`. `HOP_RE` recognised only the recursive spelling,
#: so the file's plain hops (the whole `_refresh` chain, `_search`'s fan-out) were invisible: a bare
#: host interpreter planted in a private recipe reached through a PUBLIC target's plain `make _x`
#: hop exited 0 while the guard's docstring promised to follow one hop. The hop carries an OPTIONAL
#: run of make FLAGS (`-j4`, `--no-print-directory`) before the target, because the fan-out writes
#: `@make -j4 _search-nvidia …`; the caller strips the recipe-echo `@` first (HOP_AT_PREFIX) and
#: filters any line that already carries a container harness, so both spellings stay suppressed
#: together when the hop runs inside an image.
HOP_RE = re.compile(
    r"(?<![\w.$@\\/-])(?:make|\$\(MAKE\))"
    r"([ \t]*(?:-{1,2}[A-Za-z0-9_=-]+[ \t]+)*(_[A-Za-z0-9_-]+))?"
)
#: The recipe-echo prefix: `@make … _x` is the same command as `make … _x`.
HOP_AT_PREFIX = re.compile(r"^@")
SHELL_RE = re.compile(r"\$\(shell\s+([^)]*)\)", re.S)

MAX_HOP_DEPTH = 4


class Finding:
    """One bare host interpreter invocation reachable from a public target."""

    __slots__ = ("target", "line", "token", "text")

    def __init__(self, target: str, line: int, token: str, text: str) -> None:
        self.target = target
        self.line = line
        self.token = token
        self.text = " ".join(text.split())

    def __str__(self) -> str:
        return f"{self.target} (Makefile:{self.line}): [{self.token}] {self.text[:160]}"


# ---------------------------------------------------------------------------
# THE exception list — a target here is a DELIBERATE host-only seam, not an oversight.
# Every entry names WHY it stays on the host. Keep this in step with the Makefile comment block
# delimited by HOST-EXCEPTIONS-BEGIN/END; tests/test_os_agnostic_make.py enforces the agreement.
# ---------------------------------------------------------------------------
EXCEPTIONS: dict[str, str] = {
    # --- image build / selection: these ARE the docker seam; they cannot run in a container ---
    "image-tags": "selects the runner tags through the host docker CLI",
    "image-ensure": "pulls/builds the runner images (host docker)",
    "image-ensure-base": "pulls/builds the base image (host docker)",
    "image-ensure-test": "pulls/builds the test image (host docker)",
    "announce-image-fallback": "posts on the PR about fallback images (needs gh)",
    "agent-image-ref": "prints GHCR refs for the agent image",
    "agent-image-push-check": "proves the ambient credential can push (host docker)",
    "publish-agent-image": "builds/pushes the agent image (privileged host act)",
    "agent-image-smoke": "proves the agent image carries every provisioned profile",
    "agent-image-published-check": "strict owner check on the published agent image",
    "rebuild-decision": "the built/publish decision itself (host docker + date)",
    "openspec-image": "pulls/builds the OpenSpec CLI image (host docker)",
    "python-env-image": "pulls/builds the python-env image (host docker)",
    "openspec-manifest-check": "reads a published manifest (host docker)",
    "image-manifest-check": "reads a published manifest (host docker)",
    # --- gh / GitHub-state bound: they need the runner's `gh` + token; the image has no gh ---
    "openspec-archive-check": "reads GitHub state (gh)",
    "file-findings": "files issues (gh)",
    "findings-check-for-pr": "reads the webhook payload at $GITHUB_EVENT_PATH",
    "pr-closure": "reads the webhook payload at $GITHUB_EVENT_PATH",
    "verify-closure": "reads GitHub state after a merge (gh)",
    "pr-health": "reads open-PR state (gh)",
    "pr-draft-check": "reads open-PR draft state (gh)",
    "auto-merge-rebase": "rebases and pushes a branch (gh + git)",
    "auto-merge-head-check": "re-reads the PR head (gh)",
    "keeper-pr": "lands a keeper branch + PR (gh + git)",
    "data-gap-issue": "files an issue (gh)",
    "data-gap-baseline": "writes the gap baseline as the caller",
    "refresh-run-block": "reads the run's job timestamps (gh api)",
    "comment-monitor": "reads/acts on comments (gh)",
    "comment-watch": "watches comments (gh)",
    "issue-queue": "reads issue labels/state (gh)",
    "issue-pick": "picks from the queue (gh)",
    "issue-skip-note": "comments on a held issue (gh)",
    "issue-state": "reads the issue state (gh)",
    "issue-verdict": "labels/closes an issue (gh)",
    "issue-outcome": "comments on the worked issue (gh)",
    "issue-thread": "reads the whole thread (gh)",
    "sweep-alarm": "reads the sweep's runs (gh)",
    "queued-alarm": "reads queued jobs (gh)",
    "pipeline-failure-attribute": "attributes a ledger row (gh)",
    "code-review-scan": "reads the tree for the review bot (gh)",
    "code-review-file": "files review issues (gh)",
    "review-issue-pick": "reads the queue (gh)",
    "review-issue-mark": "labels + comments (gh)",
    "review-issue-guard": "reads the window state (gh)",
    "review-issue-body-hash": "reads the issue body (gh)",
    "review-issue-check-markers": "reads the issue body (gh)",
    "review-issue-finish": "removes the label (gh)",
    "bot-health": "reads the bot pipelines' runs (gh)",
    "freshness-alarm": "reads snapshots + scheduled runs (gh)",
    "master-alarm": "reads the newest master run (gh)",
    "ghost-run-alarm": "reads concluded runs (gh)",
    "owed-rows-check": "reads every open issue's thread (gh)",
    "check-branch-protection": "reads branch protection (gh)",
    "pipeline-failure-guard-check": "reads the ledger + closed issues (gh)",
    "pipeline-failure-issue": "reads failing runs + logs (gh)",
    "hermes-pin-freshness": "reads the upstream release channel (gh)",
    "hermes-pin-channel-record": "records the live release payload (gh)",
    "free-model-refresh-pr-body": "composes the refresh PR body (gh)",
    "model-type-report": "reports model types from the store (fleet host state)",
    "dispatch-check": "reads the host dispatch registry",
    "fleet-host-sync-check": "compares the HOST profile home with the tree",
    "fleet-host-reconcile": "repairs the host profile mirrors",
    "watch-monitor": "the heartbeat monitor loop (long-running host process)",
    "agent-profile-provision": "provisions profiles in the host Hermes home",
    "agent-aux-local-sync": "syncs host auxiliary state",
    "agent-model-chain-check": "reads the host fleet model chain",
    "agent-model-chain-report": "reads the host fleet model chain",
    "agent-profile-model-render": "renders the fleet model chain",
    # --- host git identity / worktree: must read the HOST `.git` ---
    "base-check": "asserts this checkout IS the fetched base (host git)",
    "branch-adopt": "cuts/adopts a branch (host git)",
    "base-rebase": "rebases a branch (host git)",
    "base-advance": "advances a branch (host git)",
    "refresh-sync": "fetches/merges the refresh base (host git)",
    "refresh-require-tip": "asserts the base is the tip (host git)",
    "worktree-new": "creates a worktree (host git)",
    "worktree-resume": "resumes a worktree (host git)",
    "git-identity": "writes the host git identity",
    # --- cheapest pre-image-ensure guards: run BEFORE any image exists, by design ---
    "lint": "first gate in validate; must run before image-ensure",
    "lint-fix": "repair half of lint; host-side",
    "check-commit-authorship": "git-only authorship guard",
    "commit-authorship-report": "git-only authorship report",
    "pr-message-check": "pr-closure.yml runs it before any image-ensure",
    "issue-message-check": "pr-closure.yml runs it before any image-ensure",
    "commit-message-check": "pr-closure.yml runs it before any image-ensure",
    "check-conflict-markers": "git-only; part of lint",
    "check-pytest-imports": "stdlib AST scan; part of lint",
    "check-counter-parity": "stdlib scan; part of lint",
    "check-makefile-knobs": "stdlib scan; part of lint",
    "check-workflow-guards": "executes the guards; part of lint",
    "check-gh-json-fields": "stdlib scan; part of lint",
    "check-working-files": "stdlib scan; part of lint",
    "reset-working-files": "unstage helper; part of lint",
    "check-no-bare-host-python": "this guard itself (host-side by design, like lint)",
    # --- host docker / orchestration + local probes ---
    "security-scan-self-test": "runs grype on the host",
    "secret-scan": "runs gitleaks on the working tree",
    "secret-scan-history": "runs gitleaks over history",
    "secret-scan-self-test": "selftest of the secret scanner",
    "agent-hermes-smoke": "offline smoke of the agent image path (host docker)",
    "local-endpoint-probe": "probes a LOCAL endpoint (host network)",
    "local-endpoint-probe-check": "reads the local probe history",
    "qa-report": "bash driver over the QA targets",
    "free-model-refresh": "writes the free-model store as the caller",
}


def parse_makefile(text: str) -> tuple[dict[str, list[tuple[int, str]]], dict[str, list[tuple[int, str]]]]:
    """`{target: [(lineno, recipe_line), …]}` and `{macro_name: [(lineno, body_line), …]}`."""
    targets: dict[str, list[tuple[int, str]]] = {}
    macros: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        lineno = i + 1
        if line.startswith("define "):
            name = line.split()[1]
            body: list[tuple[int, str]] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("endef"):
                body.append((i + 1, lines[i]))
                i += 1
            macros[name] = body
            i += 1
            continue
        name = architecture_bot.target_at_line(line)
        if name is not None:
            current = name
            targets.setdefault(name, [])
            i += 1
            continue
        if line.startswith("\t") and current is not None:
            targets[current].append((lineno, line[1:]))
        elif line and not line.startswith("\t") and not line.startswith("#"):
            current = None
        i += 1
    return targets, macros


def logical_lines(rows: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Join backslash continuations, keeping the FIRST physical line number."""
    out: list[tuple[int, str]] = []
    buf = ""
    start = None
    for lineno, text in rows:
        if start is None:
            start = lineno
        if text.endswith("\\"):
            buf += text[:-1] + " "
        else:
            buf += text
            out.append((start, buf))
            buf = ""
            start = None
    if buf:
        out.append((start or 0, buf))
    return out


CALL_RE = re.compile(r"\$\(call\s+([A-Za-z0-9_]+)\s*,")


def bare_hits(segment: str) -> list[str]:
    """Interpreter tokens in ONE pipeline/list segment with no container harness on it."""
    if any(token in segment for token in HARNESS_TOKENS):
        return []
    return [m.group(1) for m in INTERP_RE.finditer(segment)]


def walk(target: str, targets, macros, seen=None, depth=0) -> list[Finding]:
    """Every bare host invocation this target reaches.

    Its own recipes, the bodies of any `$(call NAME,…)` macros those recipes invoke (analysed as
    SEPARATE lines, so a harness in the caller's argument cannot launder a bare command inside the
    macro body), and one make hop into a private `_x` recipe — BOTH spellings (#1596).
    """
    if seen is None:
        seen = set()
    if target in seen or depth > MAX_HOP_DEPTH:
        return []
    seen = seen | {target}
    found: list[Finding] = []
    macros_seen: set[str] = set()
    queue: list[tuple[str, str]] = [("target", target)]
    while queue:
        kind, name = queue.pop(0)
        rows = targets.get(name, []) if kind == "target" else macros.get(name, [])
        for lineno, logical in logical_lines(rows):
            stripped = logical.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Blank the call sites, then analyse each macro body on its own line.
            blanked = CALL_RE.sub(" @@CALL@@ ", logical)
            for segment in SEGMENT_SPLIT.split(blanked):
                for token in bare_hits(segment):
                    found.append(Finding(target, lineno, token, stripped))
            for call in CALL_RE.finditer(logical):
                macro = call.group(1)
                if macro in macros and macro not in macros_seen:
                    macros_seen.add(macro)
                    queue.append(("macro", macro))
            # A make hop reaches the private recipe too — `$(MAKE) _x` AND the plain `make _x`
            # spelling the file itself uses (`_refresh`'s whole chain, `_setup`'s registers; #1596).
            # A HARNESSED hop (`$(DOCKER_RUN) make _x`) is a container already, so its private
            # recipe's host-looking commands run inside the image.
            if kind == "target" and not any(token in blanked for token in HARNESS_TOKENS):
                # The recipe-echo `@` is not part of the command, so drop it before matching.
                for hop in HOP_RE.finditer(HOP_AT_PREFIX.sub("", blanked)):
                    private = hop.group(2)
                    if private in targets:
                        queue.append(("target", private))
    return found


def shell_exec_findings(text: str) -> list[Finding]:
    """Parse-time `$(shell python3 …)` execs run before ANY container starts — always in scope."""
    out: list[Finding] = []
    for lineno, line in enumerate(text.split("\n"), 1):
        for match in SHELL_RE.finditer(line):
            body = match.group(1)
            if any(token in line for token in HARNESS_TOKENS):
                continue
            for token in bare_hits(body):
                out.append(Finding("<$(shell)>", lineno, token, line.strip()))
    return out


def public_targets(targets) -> list[str]:
    return sorted(t for t in targets if not t.startswith("_") and not t.startswith("."))


def violations(text: str) -> tuple[list[Finding], int]:
    """`(findings, public_target_count)` for one Makefile's text."""
    targets, macros = parse_makefile(text)
    findings: list[Finding] = []
    for target in public_targets(targets):
        if target in EXCEPTIONS:
            continue
        findings.extend(walk(target, targets, macros))
    findings.extend(shell_exec_findings(text))
    # De-duplicate (a target can reach the same line through several paths).
    unique = {(f.target, f.line, f.token, f.text): f for f in findings}
    return sorted(unique.values(), key=lambda f: (f.target, f.line, f.token)), len(public_targets(targets))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when a public make target reaches a bare host python3/pip/uv.")
    parser.add_argument("--root", default=".", help="repository root holding the Makefile (default: cwd)")
    parser.add_argument("--makefile", default=None, help="explicit Makefile path (overrides --root)")
    parser.add_argument("--list-exceptions", action="store_true", help="print the documented host-only exception list")
    args = parser.parse_args(argv)

    if args.list_exceptions:
        for name in sorted(EXCEPTIONS):
            print(f"{name}\t{EXCEPTIONS[name]}")
        print(f"{len(EXCEPTIONS)} documented host-only exception(s)")
        return 0

    path = Path(args.makefile) if args.makefile else Path(args.root) / "Makefile"
    if not path.is_file():
        print(f"[no-bare-host-python] FAIL: no Makefile at {path}", file=sys.stderr)
        return 2
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[no-bare-host-python] FAIL: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    findings, public_count = violations(text)
    exceptions = len(EXCEPTIONS)
    if findings:
        for finding in findings:
            print(f"[no-bare-host-python] FAIL {finding}")
        print(f"[no-bare-host-python] {len(findings)} bare host invocation(s) reachable from a "
              f"non-exception public target ({public_count} public, {exceptions} exceptions)")
        return 1
    print(f"[no-bare-host-python] OK: no public target outside the {exceptions} documented "
          f"exceptions reaches a bare host python3/pip/uv ({public_count} public targets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
