# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## What this is

- **`plugin/`** — Rust Margrete plugin that runs a TCP/protobuf RPC **server** inside Margrete
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

## Plugin (Rust) commands

Prerequisites: MSVC (`x86_64-pc-windows-msvc`) and a stable Rust toolchain (`rustfmt`, `clippy`).

```bash
cd plugin

cargo fmt
cargo clippy --all-targets -- -D warnings
cargo test
cargo build --release
```

Output DLL: `plugin/target/release/margrete_rpc.dll`. `.\build.ps1 -Publish` copies the DLL and `margrete_rpc.ini` to `publish/`.

From the repo root:

```bash
.\build.ps1 -Test -Publish
.\format.ps1
```

The `plugin/margrete/` submodule is the ABI header reference only — do not compile it.

## Development Notes

- Follow conventional commit style: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
