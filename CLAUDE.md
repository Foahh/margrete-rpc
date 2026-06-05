# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Overview

**Margrete RPC** is a plugin + SDK system that exposes scriptable chart editing for Margrete via a TCP/protobuf RPC server.

- **Plugin** (`plugin/`): C++20 DLL that runs as a Margrete plugin, hosts a TCP server, translates RPC calls to Margrete SDK operations
- **SDK** (`sdk/`): Python 3.12+ client library for chart scripting; provides high-level chart objects, transaction management, and time/position conversions
- **Proto** (`proto/`): protobuf message definitions (`margrete.rpc.v1`) used for wire protocol between plugin and SDK

## Building & Testing

### Plugin (C++)

The plugin uses **CMake** with vcpkg for dependency management.

**Prerequisites:**
- Visual Studio 2022+
- CMake 3.30+
- vcpkg (set `VCPKG_ROOT` environment variable)

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

## Architecture

### Plugin Components

**Core responsibilities by file:**

- **SocketServer** / **FrameProtocol**: TCP listening, message framing (length-prefixed protobuf)
- **RequestRouter**: Dispatches RPC calls to handlers; returns `ErrorResponse` or typed response (see `RequestRouter::dispatch()`)
- **ServerController**: Manages server lifecycle (start/stop via UI dialog)
- **MargreteSession**: State holder for active chart editing session (current tick, undo buffer); wraps Margrete SDK calls
- **TransactionApplier**: Converts SDK-level chart changes into plugin event IDs; handles undo/redo with Margrete
- **ChartMapper**: Serializes/deserializes Margrete chart data to/from protobuf; maps plugin event indices to SDK objects
- **DiscoveryRegistry**: Records running plugin instances (host, port, instance_id); used by SDK auto-discovery
- **Config**: Reads `margrete-rpc.ini`; configures server bind host and port assignment
- **Dialog**: UI for starting/stopping server, displaying server status

**RPC message flow:**
1. Client sends `margrete.rpc.v1.Request` (with unique request_id)
2. RequestRouter dispatches by `Request.method` field
3. Handler executes (e.g., `openEdit()` fetches chart, returns `OpenEditResponse`)
4. Response is sent with matching request_id

**Transaction/Undo model:**
- `open_edit()` RPC creates a transaction: fetches current chart, captures current_tick, resets undo buffer
- Client modifies chart in transaction
- `commit()` applies changes to Margrete, pushes undo state into undoBuffer
- Margrete undo/redo stack is cleared when a new transaction begins (prevents dangling undo states)

### SDK Architecture

**Core modules:**

- **`client.py`**: `Margrete` class, main entry point; `status()`, `undo()`, `redo()`, `current_tick()`, `open_edit()`; manages socket connection and auto-discovery
- **`transaction.py`**: `EditTransaction` context manager; buffers changes, applies at commit
- **`discovery.py`**: `list_instances()`, `MargreteInstance`, `resolve_endpoint()`; polls DiscoveryRegistry for running servers
- **`_socket.py`**: Low-level socket + framing protocol (send/recv length-prefixed protobuf messages)
- **`errors.py`**: `MargreteProtocolError` (socket/frame issues), `MargreteRemoteError` (RPC errors with code), `MargreteDiscoveryError`
- **`chart/`**: Chart object models (see below)
- **`trace.py`**: Request/response logging via `Tracer` interface; `NoopTracer`, `CallbackTracer`

**Chart models** (`chart/` submodule):
- **`chart.py`**: `Chart` class containing `notes` (typed SDK note objects), `nodes` (raw node fallback), and `events`
- **`events.py`**: Event classes (`BpmEvent`, `BeatEvent`, `NoteSpeedEvent`, `TimelineSpeedEvent`)
- **`time.py`**: Time/position conversion (`t2p`, `p2t`, `d2t`, `t2d`) with beat event context
- **`note/`**: Note type modules and utilities
  - `types.py`: Note protocol and SDK note classes (`Tap`, `Flick`, `Hold`, `Air`, `Extap`, `Slide`, `Joint`)
  - `node.py`: Raw `Node` tree and factory `N` for building nodes (`N.tap()`, `N.hold()`, `N.slide_begin()`, etc.)
  - `air.py`, `ground.py`, `long.py`, `color.py`, `direction.py`, `shared.py`, `wrap.py`: Note-type-specific details
  - `shift.py`: Utilities for shifting notes/events by tick offset

**Transaction lifecycle:**
```python
with mg.open_edit("name") as tx:
    tx.chart.notes[0].x += 1  # Modifies copy
    tx.chart.events.bpm.append(BpmEvent(...))
# commit() called on __exit__, sends all changes to plugin
```

**Note object hierarchy:**
- **SDK notes**: `Note` protocol implemented by `Tap`, `Flick`, `Hold`, etc.; these are typed Python objects for normal scripting
- **raw notes**: `Node` trees built with `N.tap(...)`, `N.slide_begin(...)`, etc.; used for raw Margrete/plugin note structures
- `chart.notes` -> typed SDK note interface; `chart.nodes` -> raw node trees that could not or should not be wrapped
- Use `open_edit(raw=True)` to receive a `Chart` and work entirely with `Node` trees

**Generated code:**
- `_proto/messages_pb2.py` is generated from `proto/margrete/rpc/v1/messages.proto`
- Excluded from ruff linting (see pyproject.toml)

### Protobuf Schema

The wire protocol is defined in `proto/margrete/rpc/v1/messages.proto`. Key message types:

- `Request`: method name + arguments (e.g., `OpenEditRequest`, `CommitRequest`)
- `Response`: typed response matching the request (e.g., `OpenEditResponse` with serialized chart)
- `ErrorResponse`: error code + message for RPC failures
- `ServerStatus`: server name, version, build time
- Chart data structures: `Chart`, `Note`, `Event` (serialized as protobuf)

## Development Notes

### Dependencies

**Plugin:**
- Margrete Plugin SDK (git submodule in `plugin/margrete/`)
- Protobuf C++ (vcpkg: `protobuf`)
- Catch2 (vcpkg: `catch2`)
- Windows SDK (ws2_32, user32, comctl32, shell32)

**SDK:**
- `protobuf>=7.34,<8` - message serialization
- pytest (dev) - testing
- ruff (dev) - linting/formatting

### Key Design Decisions

1. **Auto-discovery:** SDK auto-connects to the sole running plugin instance; manual endpoint override available
2. **Port auto-assignment:** Plugin requests free port from Windows, enabling multiple Margrete instances simultaneously
3. **Undo/redo per-transaction:** Margrete undo stack is cleared on each new transaction to avoid stale undo states
4. **Raw vs typed chart modes:** `open_edit(raw=True)` for raw `Node` access when scripting does not need typed SDK note objects
5. **Event scanning limitation:** Plugin scans events linearly (tick 0 -> last_note_tick) due to Margrete SDK constraints; passed as `event_scan_extra_tick` / `event_scan_til` parameters

### Testing Strategy

**Plugin tests:**
- Unit tests for core modules (ChartMapper, TransactionApplier, FrameProtocol, Config, DiscoveryRegistry, RequestRouter)
- No full-server integration tests (would require Margrete running)

**SDK tests:**
- Unit tests for chart objects, time conversion, note shifting, transaction behavior
- Integration tests (test_client_transaction.py) require running plugin server
- Socket protocol tests (test_socket.py) for framing
- Discovery tests (test_discovery.py) check instance registry parsing

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

Follow conventional commit style: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.

## User Notes

- **Development philosophy**: The project is not yet published, so cleaner implementation and future maintainability are prioritized over backward compatibility.
