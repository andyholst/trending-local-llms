#!/usr/bin/env python3
r"""The contract <-> prose sync seam: `data/MODEL_CONTRACT.md` may not drift from
`data/model_contract.json` (issue #1394, slice A of #691).

`data/MODEL_CONTRACT.md` SUMMARISES `data/model_contract.json` and had no owner,
so it drifted silently: the field table carried 21 rows while the schema declared
23 model properties (`engine_aliases`, `measurement_model_aliases` had no row),
and the `hf`/`engines` rows said required while the schema does not require them.
A reader could not tell the shipped store shape from the prose.

This is the ONE seam. It parses the pipe-table rows of `data/MODEL_CONTRACT.md`
(`| \`field\` | yes/no | meaning |`) and compares them to
`data/model_contract.json`'s `properties.models.items`:

  * every schema property MUST have a row            — presence is a hard fail;
  * every row's Required cell MUST equal membership in `required`
                                                   — required-ness is a hard fail;
  * a row naming a property the schema does not declare FAILS as unknown.

Only presence and required-ness are read. The prose wording of a Meaning cell is
NOT parsed (the table is prose by design); nothing here writes a file (rule 3b).
The two known deltas were fixed ADDITIVELY in the same change (rule 6b): two rows
were added, two required cells corrected, nothing deleted.

Run:  python3 scripts/check_contract_prose.py [--data DIR] [--contract FILE]
                                             [--markdown FILE]
Exit: 0 = the prose and the schema agree, 1 = drift findings, 2 = undecidable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: A row of the contract's field table: ``| `field` | yes/no | meaning |``.
#: Only the first two cells are read; the Meaning cell is prose by design.
ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]*?)\s*\|")

#: The Required cell's vocabulary. `yes`/`no` are the table's spellings; the
#: neighbouring `true`/`false` are accepted so a writer who reaches for JSON's
#: spelling is not read as drift. Anything else is a finding.
_REQUIRED = {"yes": True, "true": True, "no": False, "false": False}


def parse_rows(markdown: str) -> dict[str, str]:
    """`{field: required_cell}` for every pipe-table row that names a backticked field."""
    rows: dict[str, str] = {}
    for line in markdown.splitlines():
        m = ROW.match(line)
        if m:
            rows[m.group(1)] = m.group(2).strip()
    return rows


def model_items(schema: dict) -> dict:
    """The model-object shape: `{property: is_required}` for `properties.models.items`.

    Raises `KeyError`/`TypeError` when the schema does not carry that shape — the
    caller turns it into an undecidable exit rather than a silent clean.
    """
    items = schema["properties"]["models"]["items"]
    properties = items.get("properties") or {}
    required = set(items.get("required") or [])
    return {name: (name in required) for name in properties}


def problems(rows: dict[str, str], items: dict[str, bool]) -> list[str]:
    """Named, actionable drift findings. Empty means the prose agrees with the schema."""
    out: list[str] = []

    # Presence: a schema property with no prose row — the drift that went unnoticed.
    missing = sorted(set(items) - set(rows))
    out += [f"schema property `{p}` has NO row in data/MODEL_CONTRACT.md "
            f"(add `| `{p}` | ... |`)" for p in missing]

    # Unknown rows: prose naming a property the schema does not declare.
    unknown = sorted(set(rows) - set(items))
    out += [f"data/MODEL_CONTRACT.md names `{p}`, which model_contract.json does NOT declare"
            for p in unknown]

    # Required-ness, BOTH directions: a cell that disagrees with the schema names
    # both sides, so a red gate says what each side actually says.
    for prop in sorted(set(rows) & set(items)):
        cell = rows[prop].lower()
        wanted = items[prop]
        if cell not in _REQUIRED:
            out.append(f"`{prop}`: the Required cell is {rows[prop]!r}, not one of "
                       f"{sorted(_REQUIRED)}")
            continue
        if _REQUIRED[cell] != wanted:
            out.append(f"`{prop}`: MODEL_CONTRACT.md says required="
                       f"{'yes' if _REQUIRED[cell] else 'no'} but model_contract.json "
                       f"{'REQUIRES it' if wanted else 'does NOT require it'}")
    return out


def check(data_dir: Path | None = None, contract: Path | None = None,
          markdown: Path | None = None) -> list[str]:
    """Drift findings for the real tree, or for a fixture pair passed explicitly.

    An absent file, an unreadable file or a schema without the models-items shape
    is a finding, never a vacuous clean — a guard that cannot read its input must
    say so (the ledger-guard model).
    """
    data = data_dir or ROOT / "data"
    cpath = contract or data / "model_contract.json"
    mpath = markdown or data / "MODEL_CONTRACT.md"
    if not cpath.is_file():
        return [f"cannot read {cpath} — the contract is undecidable without it"]
    if not mpath.is_file():
        return [f"cannot read {mpath} — the prose is undecidable without it"]
    try:
        schema = json.loads(cpath.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot parse {cpath}: {exc}"]
    try:
        md = mpath.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {mpath}: {exc}"]
    try:
        items = model_items(schema)
    except (KeyError, TypeError) as exc:
        return [f"{cpath} has no properties.models.items shape ({exc!r}) — "
                "the check cannot compare a contract that declares no model object"]
    return problems(parse_rows(md), items)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--data", default=None, help="store data directory (default: <root>/data)")
    ap.add_argument("--contract", default=None, help="the JSON Schema (default: <data>/model_contract.json)")
    ap.add_argument("--markdown", default=None, help="the prose (default: <data>/MODEL_CONTRACT.md)")
    args = ap.parse_args(argv)

    data = Path(args.data) if args.data else ROOT / "data"
    cpath = Path(args.contract) if args.contract else data / "model_contract.json"
    mpath = Path(args.markdown) if args.markdown else data / "MODEL_CONTRACT.md"

    found = check(data, cpath, mpath)
    rows = parse_rows(mpath.read_text(encoding="utf-8")) if mpath.is_file() else {}
    items = model_items(json.loads(cpath.read_text(encoding="utf-8"))) \
        if cpath.is_file() else {}
    if found:
        print(f"[contract-prose] FAIL {len(found)} drift finding(s) between "
              f"MODEL_CONTRACT.md ({len(rows)} rows) and model_contract.json "
              f"({len(items)} properties):")
        for line in found:
            print(f"  - {line}")
        print("  Fix the prose (or the schema) so a reader sees one shape.", file=sys.stderr)
        return 1
    print(f"[contract-prose] OK: every model_contract.json property has a MODEL_CONTRACT.md "
          f"row and every Required cell matches the schema's required array "
          f"({len(items)} properties / {len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
