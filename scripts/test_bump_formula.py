#!/usr/bin/env python3
"""Finite command-surface controls; no API, downloads, builds, or remote writes."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch
import bump_formula as bump

# Keep these mocked releases stable when an actual formula bump changes the tree.
ORIGINAL = re.sub(r'/v[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz', '/v0.43.0.tar.gz',
                  Path(bump.FORMULA).read_text())
CASES = [
    ("up-to-date", {}),
    ("no downgrade", {"tag": "v0.42.0"}),
    ("numeric behind", {"tag": "v0.100.0", "writes": True}),
    ("new stable release", {"tag": "v0.44.0", "writes": True}),
    ("existing PR", {"tag": "v0.44.0", "pr": True}),
    ("malformed formula", {"bad_formula": True, "error": True}),
    ("cross-repo PR refused", {"tag": "v0.44.0", "pr": True, "cross": True, "error": True}),
    ("retry pushed branch", {"tag": "v0.44.0", "remote": True, "writes": True}),
    ("unexpected pushed branch", {"tag": "v0.44.0", "remote": True, "bad_branch": True, "error": True}),
    ("validation bump", {"old": True, "base": "automation/validation-1297-test", "writes": True}),
    ("invalid base", {"base": "other", "error": True}),
    ("schedule cannot validate", {"event": "schedule", "base": "automation/validation-1297-test", "error": True}),
    ("non-main dispatch", {"ref": "refs/heads/other", "error": True}),
    ("prerelease", {"prerelease": True, "error": True}),
    ("malformed tag", {"tag": "v0.44.0;bad", "error": True}),
    ("API error", {"failure": ("gh", "api"), "error": True}),
    ("dirty checkout", {"dirty": True, "error": True}),
    ("download error", {"tag": "v0.44.0", "failure": ("curl",), "error": True}),
    ("git push error", {"tag": "v0.44.0", "failure": ("git", "push"), "error": True}),
    ("PR error", {"tag": "v0.44.0", "failure": ("gh", "pr", "create"), "error": True}),
]

for name, case in CASES:
    calls, bodies, output = [], [], io.StringIO()
    base = case.get("base", "") or "main"
    tag = case.get("tag", "v0.43.0")
    formula = ORIGINAL.replace("v0.43.0", "v0.41.0") if case.get("old") else ORIGINAL
    if case.get("bad_formula"):
        formula = formula.replace("sha256", "missing_checksum")
    branch = f"automation/bump-eigenscript-{tag[1:]}"
    if base != "main":
        branch += "-" + base.replace("/", "-")

    def command(args, **kwargs):
        calls.append(args)
        if args[:3] == ("gh", "pr", "create"):
            assert "--body" not in args and "--body-file" in args, name
            bodies.append(Path(args[args.index("--body-file") + 1]).read_text())
        failure = case.get("failure")
        if failure and args[:len(failure)] == failure:
            raise subprocess.CalledProcessError(1, args)
        text = ""
        if args[:2] == ("gh", "api"):
            text = json.dumps({"tag_name": tag, "draft": False, "prerelease": case.get("prerelease", False)})
        elif args[:2] == ("git", "show"):
            text = formula
            if args[2].startswith("FETCH_HEAD:") and not case.get("bad_branch"):
                text = formula.replace("v0.43.0", tag)
                text = re.sub(r'sha256 "[0-9a-f]{64}"', f'sha256 "{hashlib.sha256(b"mock release archive\n").hexdigest()}"', text)
        elif args[:2] == ("git", "diff"):
            text = bump.FORMULA
        elif args[:2] == ("git", "ls-remote") and case.get("remote"):
            text = "mock remote ref"
        elif args[:2] == ("git", "status") and case.get("dirty"):
            text = " M README.md"
        elif args[:3] == ("gh", "pr", "list"):
            text = json.dumps([{"url": "https://github.com/" + bump.TAP + "/pull/99", "isCrossRepository": case.get("cross", False),
                                "baseRefName": base, "headRefName": branch}] if case.get("pr") else [])
        elif args[0] == "curl":
            assert args[-1] == bump.ARCHIVE + tag + ".tar.gz", name
            Path(args[args.index("--output") + 1]).write_bytes(b"mock release archive\n")
        return subprocess.CompletedProcess(args, 0, stdout=text)

    with tempfile.TemporaryDirectory(prefix="bump-check-") as temporary:
        previous = Path.cwd()
        os.chdir(temporary)
        try:
            Path("Formula").mkdir()
            Path(bump.FORMULA).write_text(formula)
            env = {"GITHUB_REPOSITORY": bump.TAP, "GITHUB_EVENT_NAME": case.get("event", "workflow_dispatch"),
                   "GITHUB_REF": case.get("ref", "refs/heads/main"), "VALIDATION_BASE": case.get("base", "")}
            failed = False
            with patch.dict(os.environ, env, clear=True), patch.object(subprocess, "run", command), contextlib.redirect_stdout(output):
                try:
                    bump.main()
                except (ValueError, subprocess.SubprocessError):
                    failed = True
            assert failed == case.get("error", False), (name, output.getvalue())
            creates = [c for c in calls if c[:3] == ("gh", "pr", "create")]
            for create in creates:
                assert not Path(create[create.index("--body-file") + 1]).exists(), name
            if not failed:
                assert len(creates) == int(case.get("writes", False)), name
                if creates:
                    assert creates[0][creates[0].index("--base") + 1] == base, name
                    expected = hashlib.sha256(b"mock release archive\n").hexdigest()
                    assert len(bodies) == 1 and expected in bodies[0], name
                    assert bodies[0].startswith(f"Update EigenScript to [{tag}]("), name
                    assert f"[tag archive]({bump.ARCHIVE}{tag}.tar.gz).\n\n" in bodies[0], name
                    assert "\n\nSHA-256 " in bodies[0] and "\n\nMaintainer: approve pending" in bodies[0], name
                    assert ("\n\nValidation only:" in bodies[0]) == bool(case.get("base")), name
                    if not case.get("remote"):
                        assert f'sha256 "{expected}"' in Path(bump.FORMULA).read_text(), name
                else:
                    assert not any(c[0] == "curl" or c[:2] == ("git", "push") for c in calls), name
                    assert Path(bump.FORMULA).read_text() == formula, name
        finally:
            os.chdir(previous)
    print(f"PASS {name}")
print(f"BUMP_CHECKS_DONE passed={len(CASES)} examined={len(CASES)}")
