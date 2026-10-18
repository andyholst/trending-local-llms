#!/usr/bin/env python3
"""No secret VALUE may reach a log, a summary or a process list — for every key, not just one.

Every key this repo uses travels the same way: a CI secret, `docker run -e VAR` (the NAME, never `VAR=value`), and a
guard that echoes only the name when it is missing. That convention is easy to break in one line —
`echo "$HF_TOKEN"`, a `set -x` in a script that reads a key, `${{ secrets.X }}` interpolated into a
`run:` block instead of an `env:` — and nothing caught it.

What the rule is really about:

* **GitHub masks a registered secret in its own logs, and that is not enough.** Masking is a filter
  over the log stream, not a property of the code: a value that is transformed (base64, a URL, a
  slice) sails past it, and nothing is masked in a log the job uploads itself.
* **A value on a command line is public to the machine.** `docker run -e KEY=$KEY` puts it in `ps`
  and in any `--debug` output, for every user of that host.

Checks (each one is a rule with a name, so a failure says what to do):

    secrets-in-run-block   `${{ secrets.X }}` — or GitHub's own `${{ github.token }}` /
                           `${{ github['token'] }}` — interpolated inside a `run:` block: it becomes
                           part of the script text and of its output — pass it through `env:` instead
    prints-secret-value    a printing command that expands a secret-shaped variable's value
                           (`echo "$HF_TOKEN"`, `printf '%s' "$NOUS_API_KEY"`)
    xtrace-with-secrets    `set -x` in a file that also reads a secret: xtrace prints every expansion
    value-in-argv          `-e VAR=$VAR` / `--build-arg VAR=$VAR` / `-e VAR=${{ … }}`: the value
                           lands in the process list, not only in the environment
    env-dump               a bare `env` / `printenv` whose output reaches a log
    key-shaped-literal     something that looks like a real credential, committed
    whole-stdout-into-output-file
                           a command's WHOLE stdout redirected into `$GITHUB_OUTPUT`
                           (a pipeline, or a `$(…)` substitution, ending in
                           `>> "$GITHUB_OUTPUT"`): the file must hold `key=value` only.
                           `make` echoes its recipe line, which is enough to fail the
                           step with `Invalid format` and throw away the work behind it
                           (issue #346, runs 39026771566 / 39040036748), and every byte
                           a target prints lands in the output file
    whole-stdout-into-log  a command piped into `tee /dev/stderr`: the same whole
                           stream, copied into the job log instead — GitHub masks
                           registered values only, so a transformed one sails past
                           (rule 3d)

Commands:
    check_secret_output.py check     exit non-zero on any violation (the `ci-unit` gate)
    check_secret_output.py report    every file scanned, and the secret-shaped variables it uses

Usage:
    python3 scripts/check_secret_output.py check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The variables that carry a credential in this repo (by name — the values never appear here).
SECRET_VARS = (
    "NOUS_API_KEY", "NOUS_PORTAL_API_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "FIXBOT_DISPATCH_TOKEN", "HF_TOKEN", "TYPESAFE_API_KEY", "FIRECRAWL_API_KEY",
)
SECRET_ALT = "|".join(SECRET_VARS)

#: A printing command whose output goes to a terminal or a log (a redirect is a file, not output).
PRINTING = re.compile(r"^(?:@|-)?\s*(?:echo|printf|say|warn|annotate|print|sys\.stdout\.write|"
                      r"logger(?:\.\w+)?)\b")
#: The value of a secret-shaped variable, however it is spelled.
SECRET_VALUE = re.compile(rf"\$\{{?(?:{SECRET_ALT})\b")
#: Concatenated / embedded in a bigger expansion (`${KEY:-}`, `"prefix$VAR"`).
SECRET_EXPANSION = re.compile(rf"\$\{{?(?:{SECRET_ALT})(?::[-][^}}]*)?\}}?")
#: A value handed over on a command line instead of through the environment.
VALUE_IN_ARGV = re.compile(rf"(?:-e|--env|--build-arg)\s+(?:{SECRET_ALT})=\S")
#: Anything that looks like a live credential (second alarm). The BODY must be a bare alphanumeric
#: run: a real token has no `_` or `-` after its prefix, while the fixtures this repo writes look
#: like names (`hf_get_wrapped`, `hf_download_stall`) or carry separators
#: (`jev-NEVER-PRINT-THIS-…`) — measured against the 13 hits the loose pattern produced, all of
#: which were fixture names. A deliberate test value can still be committed: mark its file with
#: `# secret-output: test value` and the check accepts it there, visibly.
KEY_SHAPED = re.compile(r"(?:hf_|sk-|sk_|jev-)[A-Za-z0-9]{20,}")

#: A PYTHON script that pulls a secret's value out of the environment into a local name
#: (issue #351: the scripts wired to key values must be asserted too, not only the shell).
PY_ENV_READ = re.compile(rf"^\s*([A-Za-z_]\w*)\s*=\s*os\.(?:environ(?:\.get)?|getenv)\s*[\[\(]\s*['\"]({SECRET_ALT})['\"]")
#: A printing call, in Python's spelling.
PY_PRINTER = re.compile(r"(?:^|[^\w])(?:print|breakpoint|logging\.\w+|logger\.\w+|sys\.(?:stdout|stderr)\.write)\s*[\(\.]")

#: A command's stream redirected into a LOG FILE — the capture shape. Safe ONLY together with the
#: redactor in the same `run:` block (issue #351).
LOG_REDIRECT = re.compile(r"(?<![0-9])>{1,2}\s*['\"]?([\w./-]+\.log)\b")
#: A command that PRINTS a captured log file: the raw stream, on the console. Anchored to the
#: start of a line (a `run:` block is one string, so `^` needs MULTILINE), a pipeline stage or a
#: substitution.
LOG_PRINT = re.compile(r"(?:^|[|;&]\s*|\$\()\s*(?:cat|head|tail|less|more|strings|sed|awk|grep)\b[^|]*?\b([\w./-]+\.log)\b", re.MULTILINE)
#: The ONE thing allowed to read a captured log: the redactor, reached through `make`.
LOG_REDACTOR = re.compile(r"\b(?:make\s+scrub-log|scripts/scrub_log\.py)\b")
#: A `make` target that runs the AGENT, invoked as a command in a workflow step: its whole stream
#: would become that step's console log. (`hermes-smoke` is excluded: it is a bounded routing probe
#: whose reply is the point.)
AGENT_STREAM_MAKE = re.compile(
    r"(?:^|[;&|]|\$\()\s*(?:-\s*)?(?:run:\s*)?(?:@\s*)?make\s+"
    r"(?:implement-issue|review-issue|review-issue-window"
    r"|search-(?:nvidia|metal|cpu|amd|\$+[{(])|\$+[{(])"
    r"(?![-.\w])",
    re.MULTILINE)
#: The seam a public agent target calls instead of repeating the redaction (issue #355).
SCRUB_SEAM = "scrubbed_run"
#: The public targets whose stream is NOT captured by a workflow step, so the target itself must
#: scrub it (issue #355). `implement-issue` / `review-issue*` are captured + redacted by their own
#: steps; each target therefore has exactly ONE owner of its stream.
AGENT_TARGETS_TO_SCRUB = ("search-nvidia", "search-metal", "search-cpu", "search-amd", "search", "fix")
#: A public target's recipe, for the rule that reads it.
_TARGET_RECIPE = re.compile(r"^(?P<name>[A-Za-z][\w.%/-]*):[^\n]*\n(?P<body>(?:\t.*\n|\r?\n(?=\t))*)",
                            re.MULTILINE)


def seam_redacts(makefile_text: str) -> bool:
    """Does the `scrubbed_run` seam itself actually call the redactor? (issue #355)

    A target that calls the seam is safe only while the seam redacts — so the seam is a rule of its
    own, or gutting one function would silently un-cover every target that trusts it.
    """
    m = re.search(rf"^define\s+{SCRUB_SEAM}\b(.*?)^endef", makefile_text, re.M | re.S)
    return bool(m) and "scrub_log.py" in m.group(1)


def public_target_scrubs(makefile_text: str, target: str) -> bool:
    """Does the public `target`'s own recipe redact the stream it captured? (issue #355)

    The seam is the target, not the caller: a workflow step, `scripts/fix_loop.sh` and a human all
    reach the agent through `make <target>`, so the redaction belongs there — and a caller that
    repeats it by hand is exactly how the fix loop was missed.
    """
    for m in _TARGET_RECIPE.finditer(makefile_text):
        if m.group("name") == target:
            body = m.group("body")
            return "scrub_log.py" in body or SCRUB_SEAM in body
    return False
#: The marker that declares deliberate, non-live credential shapes in a file (tests do this).
TEST_VALUE_MARKER = "secret-output: test value"
#: `set -x` (or `set -ex`, `set -eux`) at the START of a command — xtrace prints every expansion.
#: Anchored to a command position on purpose: the word inside a quoted `echo "… runs under set -x"`
#: is documentation, and a rule that fires on its own help text gets muted (measured).
XTRACE = re.compile(r"^\s*(?:@|-)?\s*set\s+-[a-z]*x\b")
#: A bare environment dump.
ENV_DUMP = re.compile(r"(?:^|[|;&(]\s*)(?:sudo\s+)?(?:env|printenv)\s*(?:$|[|>])")
#: A redirect to a FILE (`> path`, `>> path`), which is where a key IS allowed to live
#: (`printf '%s=%s\n' "$KEY_VAR" "$key" >> "${HERMES_HOME}/.env"`). `2>&1` is not a file.
FILE_REDIRECT = re.compile(r">>?\s*['\"]?[^\s|&>]+")
#: `${{ secrets.X }}` (any name) sitting inside a `run:` block.
RUN_SECRET_EXPR = re.compile(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)")
#: GitHub's OWN credential (issue #241): `${{ github.token }}` and the bracketed
#: `${{ github['token'] }}` / `${{ github["token"] }}` are the same secret as
#: `secrets.GITHUB_TOKEN`, and interpolating one into a `run:` block leaks it the same way — the
#: script text, `ps`, and any `--debug` output. `secrets-in-run-block` therefore matches both sources;
#: the expression that was found is named in the failure so there is nothing to guess.
RUN_GITHUB_TOKEN = re.compile(r"\$\{\{\s*github\s*(?:\.\s*token\b|\[\s*['\"]token['\"]\s*\])")

#: A pipeline whose last stage redirects into Actions' OUTPUT FILE: the file then holds a command's
#: WHOLE stdout instead of `key=value` — `make` echoing its recipe line is enough to kill the step
#: (`##[error]Invalid format`, issue #346) and every line a target prints lands in the output file.
#: The redirect must be OUTSIDE a command substitution: `echo "k=$(cmd | sed …)" >> "$GITHUB_OUTPUT"`
#: prints one computed LITERAL, which is the safe shape (measured on issue-review-bot.yml:202).
PIPE_INTO_OUTPUT = re.compile(r"\|[^|]*?(>>\s*['\"]?\$GITHUB_OUTPUT)")
#: The same whole-stdout problem through a command SUBSTITUTION (`$(make x) >> "$GITHUB_OUTPUT"`).
SUBST_INTO_OUTPUT = re.compile(r"\$\([^)]*\)\s*>>\s*['\"]?\$GITHUB_OUTPUT")
#: `… | tee /dev/stderr` (or `/dev/stdout`): copies the whole stream into the job LOG. GitHub masks
#: the values it knows, so a transformed one (base64, a URL, a slice) sails past — rule 3d.
TEE_TO_LOG = re.compile(r"\|\s*tee\s+(?:-a\s+)?['\"]?/dev/std(?:err|out)\b")


def _inside_dquotes(line: str, pos: int) -> bool:
    """True when `pos` sits inside a `"…"` string. That is the discriminator between the two
    shapes that both contain a pipe and `>> $GITHUB_OUTPUT`:

        echo "k=$(cmd | sed …)" >> "$GITHUB_OUTPUT"     pipe INSIDE the quoted argument
                                                        -> one computed literal, SAFE
        cmd | tee /dev/stderr >> "$GITHUB_OUTPUT"       pipe at top level
                                                        -> the whole stream, UNSAFE
    """
    in_q = False
    i = 0
    while i < pos:
        c = line[i]
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            in_q = not in_q
        i += 1
    return in_q

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache"}
#: Files that legitimately CONTAIN the patterns (this guard and its tests) — the only exemption,
#: because a check that exempts the things it checks is not a check.
SELF_EXEMPT = {"scripts/check_secret_output.py", "tests/test_secret_output.py", "tests/test_scrub_log.py"}
#: (test_scrub_log.py is exempt for the same reason test_secret_output.py is: it must WRITE the
#: leak shape — a stub `make` that prints a value — to prove the redactor removes it. The guard is
#: what checks the rest of the tree.)


def tracked_files(root: Path = REPO_ROOT) -> list[Path]:
    """Every text file a reviewer would call part of the repo."""
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in (".sh", ".py", ".yml", ".yaml", ".mk", ".bash", ".zsh"):
            if path.name != "Makefile":
                continue
        out.append(path)
    return out


def _run_blocks(text: str) -> list[tuple[int, str]]:
    """(line number, line) for the lines inside a workflow `run:` block (scalar or `|`)."""
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    block_indent: int | None = None
    for n, line in enumerate(lines, 1):
        s = line.strip()
        m = re.match(r"^(?:- )?run:\s*(.*)$", s)
        if m:
            rest = m.group(1).strip()
            if rest not in ("", "|", ">", "|-", ">-", "|+", ">+"):
                # An INLINE run: the command is on the `- run: <cmd>` line itself, so that line is
                # the script text — the form this collector used to skip although its docstring
                # promised "scalar or `|`" (found by issue #241's tests).
                out.append((n, line))
                block_indent = None
                continue
            block_indent = len(line) - len(line.lstrip())
            continue
        if block_indent is not None:
            if not s:
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= block_indent and not line.lstrip().startswith("run:"):
                block_indent = None
            else:
                out.append((n, line))
    return out


def _run_blocks_grouped(text: str) -> list[tuple[int, str]]:
    """(first line number, the block's whole text) for each workflow `run:` block.

    A rule about a STEP — "this block captures a stream AND redacts it" — needs the block as a
    whole, not one of its lines (issue #351).
    """
    grouped: list[tuple[int, str]] = []
    start = 0
    prev: int | None = None
    buf: list[str] = []
    for n, line in _run_blocks(text):
        if prev is not None and n != prev + 1:
            grouped.append((start, "\n".join(buf)))
            buf = []
        if not buf:
            start = n
        buf.append(line)
        prev = n
    if buf:
        grouped.append((start, "\n".join(buf)))
    return grouped


def _py_reveals_value(line: str, var: str) -> bool:
    """True when a printing line could reveal the VALUE held in `var`, not merely its presence.

    `print("NOUS_API_KEY is not set")` (the NAME, as a literal) and `print(f"present: {bool(key)}")`
    reveal nothing about the value; `print(key)` and `print(f"{key[:8]}")` do — the second is a
    slice, which is exactly the "transformed value" GitHub's mask does not cover (rule 3d).
    """
    # A quoted literal that mentions the word is text, not the variable — but an f-string's braces
    # are an interpolation, so only NON-f spans are dropped.
    stripped = re.sub(r"(?<![fF])(?:\"[^\"]*\"|'[^']*')", "", line)
    for presence_only in (rf"\bbool\(\s*{var}\s*\)", rf"\blen\(\s*{var}\s*\)",
                          rf"\b{var}\s+is\s+(?:not\s+)?None\b", rf"\bnot\s+{var}\b",
                          rf"\b{var}\s*[!=]="):
        stripped = re.sub(presence_only, "", stripped)
    return bool(re.search(rf"\b{re.escape(var)}\b", stripped))


def violations(root: Path = REPO_ROOT) -> list[str]:
    """Every way a secret value could leave the process, with the line that does it."""
    bad: list[str] = []
    #: Which public agent targets redact their own stream (issue #355) — read ONCE, and the
    #: workflow rule below consults it, so a target that self-scrubs is not flagged for it.
    _mk_path = root / "Makefile"
    _mk = _mk_path.read_text() if _mk_path.is_file() else ""
    self_scrubbing = {t for t in AGENT_TARGETS_TO_SCRUB if public_target_scrubs(_mk, t)}
    if _mk:
        if not seam_redacts(_mk):
            bad.append(f"Makefile: scrub-seam-does-not-redact — the `{SCRUB_SEAM}` seam no longer "
                       f"calls `scripts/scrub_log.py`, so every target that trusts it prints the "
                       f"agent's stream raw (issue #355)")
        for target in AGENT_TARGETS_TO_SCRUB:
            if target not in self_scrubbing:
                bad.append(f"Makefile: agent-target-does-not-scrub — `{target}` runs the agent and "
                           f"nothing redacts its stream; its recipe must capture and print only "
                           f"`scripts/scrub_log.py`'s bounded tail (the `$(call scrubbed_run,…)` "
                           f"seam — a workflow step, `fix_loop.sh` and a human all call this target, "
                           f"so a caller cannot be the one that remembers; issue #355)")
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in SELF_EXEMPT:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        is_workflow = rel.startswith(".github/workflows/")
        lines = text.splitlines()

        if any(XTRACE.search(l) for l in lines) and SECRET_VALUE.search(text):
            line = next(n for n, l in enumerate(lines, 1) if XTRACE.search(l))
            bad.append(f"{rel}:{line}: xtrace-with-secrets — `set -x` in a file that reads a "
                       f"secret prints every expansion; drop the flag or the secret")

        if TEST_VALUE_MARKER not in text:
            for m in KEY_SHAPED.finditer(text):
                line = text[:m.start()].count("\n") + 1
                bad.append(f"{rel}:{line}: key-shaped-literal — something that looks like a live "
                           f"credential is committed (shape '{m.group(0)[:6]}…'); a deliberate test "
                           f"value needs '{TEST_VALUE_MARKER}' in the file")

        if is_workflow:
            for n, line in _run_blocks(text):
                for m in RUN_SECRET_EXPR.finditer(line):
                    bad.append(f"{rel}:{n}: secrets-in-run-block — `${{{{ secrets.{m.group(1)} }}}}` "
                               f"inside `run:` becomes script text and output; pass it through `env:`")
                for m in RUN_GITHUB_TOKEN.finditer(line):
                    bad.append(f"{rel}:{n}: secrets-in-run-block — `{m.group(0)}` inside `run:` becomes "
                               f"script text and output; pass it through `env:` (`github.token` is the "
                               f"same credential as `secrets.GITHUB_TOKEN`)")
            for start, block in _run_blocks_grouped(text):
                captures = sorted(set(LOG_REDIRECT.findall(block)))
                redacted = bool(LOG_REDACTOR.search(block))
                if captures and not redacted:
                    bad.append(f"{rel}:{start}: raw-agent-log-captured — a step captures a command's "
                               f"whole stream into {', '.join(captures)} and never redacts it; capture "
                               f"is only safe WITH the redactor in the same step "
                               f"(`make scrub-log FILE={captures[0]} LOG_OUT=…`), because GitHub masks "
                               f"registered values only (issue #351, rule 3d)")
                for m in LOG_PRINT.finditer(block):
                    bad.append(f"{rel}:{start}: raw-agent-log-printed — `{m.group(0).strip()[:60]}` "
                               f"prints a captured stream ({m.group(1)}) to the console; print "
                               f"`make scrub-log`'s bounded, redacted tail instead (issue #351)")
                if not redacted:
                    for m in AGENT_STREAM_MAKE.finditer(block):
                        hit = m.group(0)
                        # A target that redacts its OWN stream is safe however it is called, so it is
                        # not a finding — and the dynamic form (`make search-${{ matrix.backend }}`)
                        # names all four legs, so it is covered when every leg self-scrubs.
                        if any(t in hit for t in self_scrubbing):
                            continue
                        if "search-$" in hit and all(
                                t in self_scrubbing
                                for t in ("search-nvidia", "search-metal", "search-cpu", "search-amd")):
                            continue
                        bad.append(f"{rel}:{start}: agent-stream-printed-raw — `{hit.strip()[:50]}` "
                                   f"runs the agent with its whole stream going to this step's console "
                                   f"log; capture it (`… > <target>.log 2>&1`) and print only "
                                   f"`make scrub-log`'s bounded tail, or make the target scrub itself "
                                   f"(issue #351/#355, rule 3d)")

        if path.suffix == ".py":
            # The scripts wired to key values: a value read out of the environment and then
            # printed is the same leak as `echo \"$KEY\"`, and a shell-shaped rule cannot see it.
            for n, line in enumerate(lines, 1):
                m = PY_ENV_READ.match(line)
                if not m:
                    continue
                var, name = m.group(1), m.group(2)
                for pn, pl in enumerate(lines, 1):
                    if pn == n or pl.strip().startswith("#"):
                        continue
                    if PY_PRINTER.search(pl) and _py_reveals_value(pl, var):
                        bad.append(f"{rel}:{pn}: prints-secret-value — `{var}` holds the value of "
                                   f"{name} (read at line {n}) and is printed; print the NAME, never "
                                   f"the value (issue #351)")

        for n, line in enumerate(lines, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if TEE_TO_LOG.search(s):
                bad.append(f"{rel}:{n}: whole-stdout-into-log — a command's whole stdout reaches the "
                           f"job log (`tee /dev/stderr`); GitHub masks registered values only, so a "
                           f"transformed one leaks. Print the parsed fields instead: {s[:80]}")
            if PIPE_INTO_OUTPUT.search(s) or SUBST_INTO_OUTPUT.search(s):
                m = PIPE_INTO_OUTPUT.search(s)
                # A pipe INSIDE a quoted argument feeds the printer's value, not the file.
                unsafe_pipe = bool(m) and not _inside_dquotes(s, m.start())
                if unsafe_pipe or SUBST_INTO_OUTPUT.search(s):
                    bad.append(f"{rel}:{n}: whole-stdout-into-output-file — a command's whole stdout is "
                               f"redirected into $GITHUB_OUTPUT; write the parsed `key=value` fields only "
                               f"(`make` echoes its recipe line, which is not key=value — issue #346): {s[:80]}")
            if PRINTING.match(s) and SECRET_EXPANSION.search(s) and not FILE_REDIRECT.search(s):
                bad.append(f"{rel}:{n}: prints-secret-value — a printing command expands a secret's "
                           f"value: {s[:80]}")
            if VALUE_IN_ARGV.search(s):
                bad.append(f"{rel}:{n}: value-in-argv — the value is on the command line (visible in "
                           f"`ps`), not only in the environment: {s[:80]}")
            if ENV_DUMP.search(s) and not s.startswith("#"):
                bad.append(f"{rel}:{n}: env-dump — a bare environment dump reaches the log: {s[:80]}")
    return bad


def report(root: Path = REPO_ROOT) -> list[dict]:
    """What each file does with a secret-shaped variable (for a maintainer reading, not a gate)."""
    rows = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in SELF_EXEMPT:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        named = sorted({m for m in re.findall(rf"\b({SECRET_ALT})\b", text)})
        if named:
            rows.append({"file": rel, "names": named,
                         "prints": bool(PRINTING.search(text) and SECRET_EXPANSION.search(text)),
                         "xtrace": bool(XTRACE.search(text))})
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="check_secret_output", description=__doc__)
    p.add_argument("cmd", choices=("check", "report"))
    p.add_argument("--root", default=str(REPO_ROOT))
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root)

    if args.cmd == "report":
        rows = report(root)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{len(rows)} file(s) name a secret-shaped variable:")
            for r in rows:
                flags = "".join("!" if r["prints"] else ".", )
                print(f"  {flags} {r['file']} — {', '.join(r['names'])}")
        return 0

    bad = violations(root)
    if bad:
        print(f"[check-secret-output] {len(bad)} violation(s):", file=sys.stderr)
        for b in bad:
            print(f"  - {b}", file=sys.stderr)
        return 1
    print(f"[check-secret-output] OK: {len(tracked_files(root))} file(s) scanned — no secret VALUE "
          f"is printed, passed on a command line, receiver of an xtrace, dumped, or committed; "
          f"secret-shaped names: {', '.join(SECRET_VARS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
