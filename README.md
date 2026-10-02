# homebrew-eigenscript

Homebrew tap for [EigenScript](https://github.com/InauguralSystems/EigenScript) — a bytecode VM language with a copy-and-patch x86-64 JIT, observer-based assignment tracking, and temporal queries.

## Install

```sh
brew tap inauguralsystems/eigenscript
brew install eigenscript
```

Then:

```sh
eigenscript path/to/script.eigs
```

## What it installs

- `eigenscript` — the interpreter + JIT
- `eigenlsp` — the LSP server (point your editor at it via the bundled VS Code / Vim grammars in [the main repo](https://github.com/InauguralSystems/EigenScript/tree/main/editors))
- The standard library at `$(brew --prefix)/lib/eigenscript/` (imported as `import calculus`, `import json`, etc.)

The formula runs the default `make install` build, so the optional HTTP/model/DB server extensions are off. `import http` works, but its server builtins (`start_server`, `route_get`, …) require the `make full` build, which the tap does not ship.

## Platforms

- **macOS Intel** (x86_64): JIT + interpreter
- **macOS Apple Silicon** (arm64): interpreter-only — the ARM64 JIT isn't written yet
- **Linux x86_64**: JIT + interpreter (Homebrew on Linux supported)

## Versioning

The tap checks the parent repo's latest stable GitHub release daily and on manual
dispatch of **Bump EigenScript formula** from `main`. When behind, it downloads
the release's tag archive, computes its SHA-256, and opens a formula bump PR in
this tap. An up-to-date formula or an existing open bump PR produces no changes.
API, download, git, and PR errors fail the workflow. No extra secret is needed:
the workflow uses this repository's `GITHUB_TOKEN`.

Approve pending brew test-bot runs if GitHub requests approval on the generated
PR, then merge after the formula checks pass. GitHub documents this
[approval requirement for token-created PRs](https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs).
The test-bot's manual dispatch runs syntax/setup checks; its formula checks run
on `pull_request`.

To validate the entire bump path without changing `main`, create a temporary
`automation/validation-1297-*` branch from current `main` and restore a historical
formula using its real release URL and checksum from git history. Dispatch
**Bump EigenScript formula** from `main` with that branch as `validation_base`.
It opens a PR targeting only the validation branch. Approve any pending test-bot
runs, confirm all three platforms' formula checks pass, repeat the dispatch to
confirm it reuses the open PR, then close the PR and delete both temporary
branches. Do not merge the validation PR. Scheduled runs always target `main`;
other manual base names are refused.

Run the small mocked automation checks with `python3 -B scripts/test_bump_formula.py`.
Use `brew install --HEAD eigenscript` to build from `main` instead.

## License

MIT, same as EigenScript itself.
