# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Overview

**Margrete RPC** is a plugin + SDK system that exposes scriptable chart editing for Margrete via a TCP/protobuf RPC server.

- **Plugin** (`plugin/`): C++20 DLL that runs as a Margrete plugin, hosts a TCP server, translates RPC calls to Margrete SDK operations
- **SDK** (`sdk/`): Python 3.13+ client library for chart scripting; provides high-level chart objects, transaction management, and time/position conversions
- **Proto** (`proto/`): protobuf message definitions (`margrete.rpc.v1`) used for wire protocol between plugin and SDK

## Building & Testing

### Plugin (C++)

The plugin uses **CMake** with vcpkg for dependency management.

**Build commands:**
```powershell
# Release build (default)
.\build.ps1

# Debug build with tests
.\build.ps1 -Configuration Debug -Test

# Publish to publish/ folder (copy DLL + INI for manual Margrete install)
.\build.ps1 -Publish

# Initialize submodules (MargretePluginSDK)
.\build.ps1 -InitSubmodules
```

**Plugin tests** use **Catch2**. Run via:
```powershell
.\build.ps1 -Configuration Debug -Test
# Or manually from build dir:
ctest -C Debug --output-on-failure
```

### SDK (Python)

The Python SDK uses **uv** for dependency management, **pytest** for testing and **ruff** for linting/formatting.

**Setup:**
```bash
cd sdk
uv sync
```

**Run tests:**
```bash
pytest                          # All tests
pytest tests/test_chart_objects.py  # Single file
pytest -k test_name             # Single test by name
pytest -v --tb=short           # Verbose with short tracebacks
```

**Type check:**
```bash
cd sdk
uv run pyright
```

**Format/lint:**
```bash
# Check formatting and lint issues
.\format.ps1 -Check

# Fix issues
.\format.ps1

# Python only (skip C++)
.\format.ps1 -SkipCpp

# C++ only (skip Python)
.\format.ps1 -SkipPython
```

**Python test configuration** is in `sdk/pyproject.toml`:
- Test paths: `sdk/tests/`
- Python path: `sdk/src/` (allows `from margrete_rpc import ...`)
- Ruff excludes: `margrete_rpc/_proto/` (generated protobuf)

## Development Notes

- Follow conventional commit style: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
- The project is not yet published, so cleaner implementation and future maintainability are prioritized over backward compatibility.


## Common Commands

```powershell
# Format all sources
.\format.ps1

# Format with check (CI-like)
.\format.ps1 -Check

# Build plugin Release + run SDK tests
.\build.ps1 && cd sdk && pytest

# Full CI flow: build plugin, run plugin tests, format check, SDK tests
.\build.ps1 -Configuration Release -Test && .\format.ps1 -Check && cd sdk && pytest

# Debug build with full test cycle
.\build.ps1 -Configuration Debug -Test -SkipVcVars
```
