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
- The standard library at `$(brew --prefix)/lib/eigenscript/` (imported as `import calculus`, `import http`, etc.)

## Platforms

- **macOS Intel** (x86_64): JIT + interpreter
- **macOS Apple Silicon** (arm64): interpreter-only — the ARM64 JIT isn't written yet
- **Linux x86_64**: JIT + interpreter (Homebrew on Linux supported)

## Versioning

The tap tracks tagged releases of the parent repo. Use `brew install --HEAD eigenscript` to build from `main` instead.

## License

MIT, same as EigenScript itself.
