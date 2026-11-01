#!/usr/bin/env python3
"""Decide whether this brew test-bot matrix leg runs --only-tap-syntax.

`brew test-bot --only-tap-syntax` runs `brew style`, `brew readall --os=all
--arch=all` and the full-tap `brew audit`. The first two do not depend on the
host, so running them on every matrix leg repeats the same check; on
macos-15-intel it cost about 5 of the leg's 11.5 minutes (hq#58, SM-HB-3).

A leg skips the step only when it is named, with a reason, in
.github/tap-syntax-skip-allowlist.txt. Any leg not named there runs it, so a
renamed or added leg runs tap-syntax by default.

The script exits 1 instead of deciding when:
  - the matrix os list cannot be read unambiguously from the workflow, or the
    matrix uses include/exclude (which this model of the legs cannot see);
  - the allowlist is missing, or an entry has no reason, is duplicated, or
    names an os that is not in the matrix (a stale entry);
  - every matrix leg is allowlisted, so tap-syntax would run nowhere;
  - the leg being decided is not in the matrix.

Usage: tap_syntax_legs.py [--workflow PATH] [--allowlist PATH] LEG
Writes tap_syntax=true|false to $GITHUB_OUTPUT when that is set.
"""
import os
import re
import sys

WORKFLOW = ".github/workflows/tests.yml"
ALLOWLIST = ".github/tap-syntax-skip-allowlist.txt"
JOB = "test-bot"
NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class LegError(Exception):
    pass


def matrix_legs(text):
    """Return the test-bot job's matrix os list, refusing any ambiguity."""
    if re.search(r"^\s+(include|exclude):", text, re.M):
        raise LegError("matrix include/exclude is not supported; list every leg in 'os: [...]'")
    lists = re.findall(r"^\s+os:\s*\[([^\]]*)\]\s*(?:#.*)?$", text, re.M)
    if len(lists) != 1:
        raise LegError(f"expected exactly one flow-style 'os: [...]' line, found {len(lists)}")
    legs = [item.strip().strip("'\"") for item in lists[0].split(",")]
    if not legs or any(not NAME.match(leg) for leg in legs):
        raise LegError(f"unreadable matrix os list: [{lists[0]}]")
    if len(set(legs)) != len(legs):
        raise LegError(f"duplicate leg in matrix os list: {legs}")
    try:
        import yaml
    except ImportError:
        return legs
    doc = yaml.safe_load(text)
    try:
        matrix = doc["jobs"][JOB]["strategy"]["matrix"]
    except (KeyError, TypeError):
        raise LegError(f"no jobs.{JOB}.strategy.matrix in the workflow") from None
    if not isinstance(matrix, dict) or set(matrix) != {"os"} or matrix["os"] != legs:
        raise LegError(f"jobs.{JOB}.strategy.matrix is {matrix!r}, not os: {legs}")
    return legs


def allowlisted(text, legs):
    """Return {leg: reason} from the allowlist text."""
    entries = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            raise LegError(f"allowlist line {number}: '{parts[0]}' has no reason")
        leg, reason = parts[0], parts[1].strip()
        if leg in entries:
            raise LegError(f"allowlist line {number}: '{leg}' is listed twice")
        if leg not in legs:
            raise LegError(f"allowlist line {number}: '{leg}' is not a matrix leg {legs} (stale entry)")
        entries[leg] = reason
    return entries


def decide(leg, workflow_text, allowlist_text):
    legs = matrix_legs(workflow_text)
    skips = allowlisted(allowlist_text, legs)
    running = [name for name in legs if name not in skips]
    if not running:
        raise LegError(f"every matrix leg {legs} is allowlisted: tap-syntax would run nowhere")
    if leg not in legs:
        raise LegError(f"leg '{leg}' is not in the matrix {legs}")
    return leg not in skips, skips.get(leg, ""), legs, running


def main(argv):
    workflow, allowlist, leg = WORKFLOW, ALLOWLIST, None
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg in ("--workflow", "--allowlist") and args:
            if arg == "--workflow":
                workflow = args.pop(0)
            else:
                allowlist = args.pop(0)
        elif leg is None and not arg.startswith("--"):
            leg = arg
        else:
            raise LegError(f"unexpected argument '{arg}'")
    if not leg:
        raise LegError("usage: tap_syntax_legs.py [--workflow PATH] [--allowlist PATH] LEG")
    try:
        with open(workflow) as handle:
            workflow_text = handle.read()
        with open(allowlist) as handle:
            allowlist_text = handle.read()
    except OSError as error:
        raise LegError(str(error)) from None
    run, reason, legs, running = decide(leg, workflow_text, allowlist_text)
    if run:
        print(f"tap-syntax runs on {leg}")
    else:
        print(f"::notice title=tap-syntax skipped on {leg}::allowlisted in {allowlist}: {reason}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as handle:
            handle.write(f"tap_syntax={'true' if run else 'false'}\n")
    print(f"TAP_SYNTAX_LEGS leg={leg} run={'true' if run else 'false'} "
          f"legs={len(legs)} running={','.join(running)}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except LegError as error:
        print(f"::error title=tap-syntax leg check::{error}")
        sys.exit(1)
