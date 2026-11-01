#!/usr/bin/env python3
"""Checks for scripts/tap_syntax_legs.py (hq#58, SM-HB-3).

Every case runs the script as the workflow does (a subprocess with a leg
argument and GITHUB_OUTPUT set) and checks its exit code and the decision it
wrote. The error cases are the ways an allowlist can make tap-syntax run
nowhere or describe legs that no longer exist.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "tap_syntax_legs.py"
REPO = HERE.parent

WORKFLOW = """name: brew test-bot
on:
  pull_request:
jobs:
  test-bot:
    strategy:
      fail-fast: false
      matrix:
        os: {matrix}
    runs-on: ${{{{ matrix.os }}}}
    steps:
      - run: brew test-bot --only-tap-syntax
"""
MATRIX = "[ubuntu-latest, macos-15-intel, macos-latest]"
SKIP_MACOS = "# comment\n\nmacos-15-intel host-independent\nmacos-latest host-independent\n"

# (name, leg, workflow matrix text, allowlist text or None for a missing file, expected decision or "error")
CASES = [
    ("listed leg skips", "macos-15-intel", MATRIX, SKIP_MACOS, "false"),
    ("unlisted leg runs", "ubuntu-latest", MATRIX, SKIP_MACOS, "true"),
    ("empty allowlist runs everywhere", "macos-latest", MATRIX, "# nothing skipped\n", "true"),
    ("quoted matrix entries", "ubuntu-latest", "['ubuntu-latest', \"macos-latest\"]  # legs",
     "macos-latest host-independent\n", "true"),
    ("renamed ubuntu leg still runs", "ubuntu-24.04", "[ubuntu-24.04, macos-15-intel, macos-latest]",
     SKIP_MACOS, "true"),
    ("every leg allowlisted", "macos-latest", MATRIX,
     SKIP_MACOS + "ubuntu-latest host-independent\n", "error"),
    ("ubuntu leg dropped from matrix", "macos-latest", "[macos-15-intel, macos-latest]", SKIP_MACOS, "error"),
    ("entry without reason", "ubuntu-latest", MATRIX, "macos-latest\n", "error"),
    ("stale entry", "ubuntu-latest", MATRIX, "macos-14 retired runner\n", "error"),
    ("duplicate entry", "ubuntu-latest", MATRIX, "macos-latest a\nmacos-latest b\n", "error"),
    ("leg not in matrix", "windows-latest", MATRIX, SKIP_MACOS, "error"),
    ("missing allowlist", "ubuntu-latest", MATRIX, None, "error"),
    ("matrix exclude", "ubuntu-latest", MATRIX + "\n        exclude:\n          - os: ubuntu-latest",
     SKIP_MACOS, "error"),
    ("block-style matrix list", "ubuntu-latest", "\n          - ubuntu-latest\n          - macos-latest",
     "", "error"),
    ("empty leg argument", "", MATRIX, SKIP_MACOS, "error"),
]


def run(leg, workflow, allowlist, output):
    env = dict(os.environ, GITHUB_OUTPUT=str(output))
    args = [sys.executable, "-B", str(SCRIPT), "--workflow", str(workflow), "--allowlist", str(allowlist)]
    return subprocess.run(args + [leg], env=env, capture_output=True, text=True)


def decision(output):
    lines = output.read_text().splitlines() if output.exists() else []
    return lines[-1].split("=", 1)[1] if lines else None


passed = 0
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    for name, leg, matrix, allowlist_text, expected in CASES:
        workflow = tmp / "tests.yml"
        allowlist = tmp / "allowlist.txt"
        output = tmp / "output"
        workflow.write_text(WORKFLOW.format(matrix=matrix))
        if allowlist.exists():
            allowlist.unlink()
        if allowlist_text is not None:
            allowlist.write_text(allowlist_text)
        if output.exists():
            output.unlink()
        result = run(leg, workflow, allowlist, output)
        detail = (name, result.returncode, result.stdout, result.stderr)
        if expected == "error":
            assert result.returncode == 1, detail
            assert "::error title=tap-syntax leg check::" in result.stdout, detail
            assert decision(output) is None, detail
        else:
            assert result.returncode == 0, detail
            assert decision(output) == expected, detail
            assert f"TAP_SYNTAX_LEGS leg={leg} run={expected} " in result.stdout, detail
        passed += 1
        print(f"PASS {name}")

    # The tree's own workflow and allowlist: every leg decides, and at least one runs.
    real_workflow = REPO / ".github/workflows/tests.yml"
    real_allowlist = REPO / ".github/tap-syntax-skip-allowlist.txt"
    sys.path.insert(0, str(HERE))
    import tap_syntax_legs
    legs = tap_syntax_legs.matrix_legs(real_workflow.read_text())
    runs = []
    for leg in legs:
        output = tmp / f"output-{leg}"
        result = run(leg, real_workflow, real_allowlist, output)
        assert result.returncode == 0, (leg, result.stdout, result.stderr)
        runs.append(decision(output))
    assert set(runs) <= {"true", "false"} and "true" in runs, (legs, runs)
    passed += 1
    print(f"PASS repository legs {dict(zip(legs, runs))}")

# Pinned population: deleting a CASES row must fail here, not shrink the count silently.
EXPECTED_EXAMINED = 16
examined = len(CASES) + 1
assert examined == EXPECTED_EXAMINED, (examined, EXPECTED_EXAMINED)
assert passed == examined, (passed, examined)
print(f"TAP_SYNTAX_LEGS_CHECKS_DONE passed={passed} examined={examined}")
