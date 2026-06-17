# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## What this is

- **`plugin/`** — C++ Margrete plugin that runs a TCP/protobuf RPC **server** inside Margrete
- **`src/margrete_rpc/`** — Python **client** package that connects to the plugin
- **`proto/`** — protobuf definitions shared by both
- **`website/`** — Fumadocs documentation site; auto-generates API reference from the Python package

## Client (Python) commands

All commands use `uv` as the project tool (the `.venv` does not have pip/pytest directly):

```bash
uv run --extra dev pytest                          # run all tests
uv run --extra dev pytest tests/test_chart_time.py # run a single test file
uv run --extra dev pytest tests/test_foo.py::test_bar  # run a single test
uv run --extra dev pyright                         # type checking
uv run --extra dev ruff check src/                 # lint
uv run --extra dev ruff format src/                # format
```

The `proto/` generated files (`src/margrete_rpc/_proto/`) are excluded from ruff and pyright — don't edit them.

## Plugin (C++) commands

Prerequisites: MSVC, vcpkg with `VCPKG_ROOT` set, Visual Studio 2026 generator.

```bash
cd plugin

# First time: configure (from plugin/ directory)
cmake --preset windows-x64

# Build the DLL (no vcvars needed, VS generator handles it)
cmake --build build --config Release

# Build + run C++ tests without touching the deployed DLL
cmake --build build --config Release --target plugin_tests
ctest --test-dir build -C Release --output-on-failure
```

Output DLL: `plugin/build/Release/margrete-rpc.dll`.

## Development Notes

- Follow conventional commit style: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
- The project is not yet published, so cleaner implementation and future maintainability are prioritized over backward compatibility.
