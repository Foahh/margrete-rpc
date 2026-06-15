# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Overview

**Margrete RPC** is a plugin + SDK system that exposes scriptable chart editing for Margrete (UMIGURI) via a TCP/protobuf RPC server.

- **Plugin** (`plugin/`): C++20 DLL that runs as a Margrete plugin, hosts a TCP server, translates RPC calls to Margrete SDK operations
- **SDK** (`src/margrete_rpc/`): Python 3.13+ client library for chart scripting; provides high-level chart objects, transaction management, and time/position conversions
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

**Python test configuration** is in `pyproject.toml`:
- Test paths: `tests/`
- Python path: `src/` (allows `from margrete_rpc import ...`)
- Ruff excludes: `margrete_rpc/_proto/` (generated protobuf)

## Architecture

### Wire Protocol

A single `.proto` file (`proto/margrete/rpc/v1/messages.proto`) defines all messages. Every request and response is wrapped in an `Envelope` with a `oneof` field selecting the payload. The plugin uses length-prefixed framing (`FrameProtocol.cpp`) over TCP. On the Python side, `_socket.py` (`SocketRpcClient`) and `_transport.py` implement the same framing.

### Plugin Component Map

```
Plugin (IMargretePluginCommand)
  └─ ServerController       lifecycle: starts/stops the TCP server thread
       ├─ SocketServer       accepts TCP connections
       ├─ FrameProtocol      length-prefixed protobuf framing per connection
       ├─ RequestRouter      dispatches Envelope → handler by oneof field
       │    ├─ MargreteSession    thin wrapper around IMargretePluginContext
       │    ├─ ChartMapper        serializes Margrete chart ↔ proto notes/events
       │    ├─ TransactionApplier applies ApplyEditRequest on Margrete's undo stack
       │    └─ RootNoteDeduper   deduplicates root-level notes after apply
       ├─ DiscoveryRegistry  writes JSON instance record to %LOCALAPPDATA%\MargreteRPC\instances\
       ├─ Config             loads margrete-rpc.ini settings
       └─ Logger             logs to file
```

### Python SDK Data Flow

```
Margrete (client.py)
  └─ open_edit(name) → EditTransaction (transaction.py)
       │  __enter__: BeginEditRequest → Chart (chart.py)
       │             pushes beat_events + tick_resolver into contextvars
       │             captures EditSnapshot (diff.py) if scan=True
       └─ __exit__ (clean): build_apply_edit_request (diff.py) → ApplyEditRequest
```

**Chart model** (`chart/chart.py`):
- `Chart.notes`: `list[ChartNote]` — either typed `Note` objects or `RawNote` trees
- `Chart.events`: `ChartEvents` — BPM, beat (time-signature), TIL, note-speed events

**Note hierarchy** (`chart/notes/`):
- `Note` is a `Protocol` (structural) defined in `shared.py`
- Ground notes (`ground.py`): `Tap`, `Extap`, `Flick`, `Damage`
- Long notes (`long.py`): `Hold`, `Slide`, `AirCrush` — each a BEGIN node with `Joint`/`AirJoint` children
- Air notes (`air.py`): `Air`, `AirHold`, `AirSlide` — attached to a parent ground/long note
- `RawNote` (`raw.py`): low-level protobuf-tree node; used with `raw=True` or for unrecognised trees
- All typed notes compose `_GeometryInfoMixin`, `_TransformMixin`, and optional `_HeightMixin` from `shared.py`, backed by `NoteInfo` (`types.py`)
- `wrap_raw_note` (`wrap.py`) converts `RawNote` → typed note on `BeginEditResponse` deserialization

**Transforms** — every `Note` has both in-place (`shift`, `scale`, `align`, `flip`, `clamp_w`) and cloning (`shifted`, `scaled`, etc.) variants that return `self` for chaining.

### Implicit Tick Resolution

Inside a `with m.open_edit() as tx:` block, `EditTransaction.__enter__` pushes the chart's `BeatEvent` list and a tick resolver into `contextvars.ContextVar`s (`time.py`). This means note constructors accept `t=(bar, beat, offset)` tuples and resolve to absolute ticks automatically — no need to thread beat events through every call. The context is restored on `__exit__`.

### Diff / Apply Modes

`open_edit()` supports three apply strategies (controlled by `scan` and `replace_all`):
- **scan=True** (default): snapshots notes+events on enter; on exit sends only the deltas (added/modified/deleted by server `_id`)
- **scan=False**: sends all notes in the final chart as upserts (no existing ids allowed)
- **replace_all=True**: strips all ids, sends every note as an upsert with `replace_all_notes=True`

### Discovery

The plugin writes a JSON file to `%LOCALAPPDATA%\MargreteRPC\instances\<id>.json` on startup (`DiscoveryRegistry.cpp`). `discovery.py` reads these files, pings each endpoint, and resolves a single instance. `Margrete()` with no arguments auto-discovers; pass `endpoint=` or `instance_id=` to target a specific server.

### Time / Position Model

`TICKS_PER_BEAT = 1920` (quarter-note resolution). Two coordinate systems:
- `Position(bar, beat, offset)` — musical position; convert with `t2p`/`p2t`
- `Interval(numerator, denominator)` — beat fraction (e.g. `(1, 4)` = quarter note); convert with `d2t`/`t2d`

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
.\build.ps1 && pytest

# Full CI flow: build plugin, run plugin tests, format check, SDK tests
.\build.ps1 -Configuration Release -Test && .\format.ps1 -Check && pytest

# Debug build with full test cycle
.\build.ps1 -Configuration Debug -Test -SkipVcVars
```
