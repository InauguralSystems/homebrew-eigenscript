#!/usr/bin/env python3
"""Open a same-tap PR for the latest stable EigenScript release."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

TAP = "InauguralSystems/homebrew-eigenscript"
UPSTREAM = "InauguralSystems/EigenScript"
FORMULA = "Formula/eigenscript.rb"
ARCHIVE = f"https://github.com/{UPSTREAM}/archive/refs/tags/"
VERSION = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(*args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          timeout=180).stdout.rstrip("\n")


def version(tag):
    require(isinstance(tag, str), "release tag must be a string")
    match = re.fullmatch("v" + VERSION, tag)
    require(match, f"unsupported stable release tag: {tag!r}")
    return tuple(map(int, match.groups()))


def main():
    require(os.environ.get("GITHUB_REPOSITORY") == TAP, "wrong repository")
    event = os.environ.get("GITHUB_EVENT_NAME")
    require(event in ("schedule", "workflow_dispatch"), "unsupported event")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "run from main")
    validation = os.environ.get("VALIDATION_BASE", "")
    require(not validation or (event == "workflow_dispatch" and re.fullmatch(
        r"automation/validation-1297-[A-Za-z0-9][A-Za-z0-9-]{0,63}", validation)),
        "validation_base must be a reserved validation branch on manual dispatch")
    base = validation or "main"
    require(not run("git", "status", "--porcelain"), "checkout must be clean")
    release = json.loads(run("gh", "api", f"repos/{UPSTREAM}/releases/latest"))
    require(isinstance(release, dict) and release.get("draft") is False and
            release.get("prerelease") is False, "expected a published stable release")
    tag = release.get("tag_name")
    latest = version(tag)
    run("git", "fetch", "--no-tags", "origin",
        f"+refs/heads/{base}:refs/remotes/origin/{base}")
    formula = run("git", "show", f"refs/remotes/origin/{base}:{FORMULA}") + "\n"
    urls = list(re.finditer(r'^  url "' + re.escape(ARCHIVE) +
                           r'(v' + VERSION + r')\.tar\.gz"$', formula, re.M))
    sums = list(re.finditer(r'^  sha256 "([0-9a-f]{64})"$', formula, re.M))
    require(len(urls) == len(sums) == 1, "expected one release URL and checksum")
    current = version(urls[0].group(1))
    print(f"base={base} formula={urls[0].group(1)} latest={tag}", flush=True)
    if current >= latest:
        print("Formula is up to date; no changes.")
        return
    branch = f"automation/bump-eigenscript-{tag[1:]}"
    if validation:
        branch += "-" + validation.replace("/", "-")
    prs = json.loads(run("gh", "pr", "list", "--repo", TAP, "--state", "open",
        "--base", base, "--head", branch, "--limit", "2", "--json",
        "number,url,isCrossRepository,baseRefName,headRefName"))
    require(isinstance(prs, list) and len(prs) <= 1, "ambiguous open bump PRs")
    if prs:
        pr = prs[0]
        require(pr.get("isCrossRepository") is False and pr.get("baseRefName") == base
                and pr.get("headRefName") == branch, "unexpected existing PR")
        print(f"Bump PR already exists: {pr['url']}")
        return
    url = ARCHIVE + tag + ".tar.gz"
    with tempfile.TemporaryDirectory(prefix="eigenscript-release-") as temporary:
        archive = Path(temporary) / "release.tar.gz"
        run("curl", "--fail", "--silent", "--show-error", "--location", "--retry", "2", "--connect-timeout",
            "15", "--max-time", "45", "--proto", "=https", "--proto-redir",
            "=https", "--output", str(archive), url)
        require(archive.stat().st_size > 0, "empty release archive")
        with archive.open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
    updated = formula.replace(urls[0].group(0), f'  url "{url}"', 1)
    updated = updated.replace(sums[0].group(0), f'  sha256 "{checksum}"', 1)
    remote = run("git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    if remote:
        run("git", "fetch", "--no-tags", "origin", f"refs/heads/{branch}")
        require(run("git", "show", f"FETCH_HEAD:{FORMULA}") + "\n" == updated and
                run("git", "diff", "--name-only", f"origin/{base}", "FETCH_HEAD")
                == FORMULA, "existing branch does not contain exactly this formula bump")
    else:
        run("git", "switch", "--create", branch, f"origin/{base}")
        Path(FORMULA).write_text(updated)
        run("git", "config", "user.name", "github-actions[bot]")
        run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        run("git", "add", "--", FORMULA)
        run("git", "commit", "--message", f"formula: bump eigenscript to {tag[1:]}")
        run("git", "push", "origin", f"HEAD:refs/heads/{branch}")
    body = (f"Update EigenScript to [{tag}](https://github.com/{UPSTREAM}/releases/tag/{tag}).\n\n"
            f"SHA-256 `{checksum}` was computed from the downloaded [tag archive]({url}).\n\n"
            "Maintainer: approve pending brew test-bot workflow runs if GitHub requests it; "
            "merge after the formula checks pass.")
    if validation:
        body += "\n\nValidation only: close this PR after checks; do not merge into main."
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="bump-pr-",
                                     suffix=".md") as body_file:
        body_file.write(body)
        body_file.flush()
        print(run("gh", "pr", "create", "--repo", TAP, "--base", base, "--head", branch,
                  "--title", f"formula: bump eigenscript to {tag[1:]}",
                  "--body-file", body_file.name))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Formula bump failed: {error}", file=sys.stderr)
        sys.exit(1)
