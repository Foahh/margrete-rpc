# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## What this is

Margrete RPC is a Margrete plugin + Python SDK for scripting chart edits programmatically. It has two parts:

- **`plugin/`** — C++ Margrete plugin that runs a TCP/protobuf RPC **server** inside Margrete
- **`src/margrete_rpc/`** — Python **client** SDK that connects to the plugin and applies chart edits
- **`proto/`** — protobuf definitions shared by both
- **`docs/`** — Fumadocs documentation site; auto-generates API reference from the Python SDK

## Python SDK commands

All SDK commands use `uv` as the project tool (the `.venv` does not have pip/pytest directly):

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

### Deploying the plugin

The user's Margrete install is `%MARGRETE_DIR%`, plugins directory `%MARGRETE_DIR%\plugins\`. While Margrete is running, the deployed DLL is locked — rebuilding produces a fresh `build/Release/margrete-rpc.dll` but the deployed copy goes stale. To test a new build: stop Margrete, copy the new DLL + INI into `plugins\`, and relaunch.

Plugin logs: `%LOCALAPPDATA%\MargreteRPC\logs\margrete-rpc-<instance>.log`
Discovery files: `%LOCALAPPDATA%\MargreteRPC\instances\`

## Python SDK architecture

### Entry point: `Margrete` and `EditTransaction`

`src/margrete_rpc/client.py` — `Margrete` is the sole entry point. It auto-discovers the running plugin via `discovery.py` (reads JSON files from `%LOCALAPPDATA%\MargreteRPC\instances\`). The key method is `open_edit()`, which returns an `EditTransaction` context manager. On clean exit the transaction diffs the chart and sends one atomic `ApplyEditRequest` to Margrete. On exception, nothing is applied.

```python
m = Margrete()                    # auto-detect running instance
with m.open_edit("label") as tx:
    tx.chart.notes.append(Tap(t=(0, 0, 0), x=0, w=4))
# changes sent here
```

### Chart model: `chart/chart.py`

`Chart` holds `notes: list[ChartNote]` and `events: ChartEvents`. Notes are either typed (`Note` subclasses) or `RawNote` trees (when the wire format isn't recognized, or when `raw=True` is passed to `open_edit`). `ChartEvents` holds BPM, beat (time-signature), TIL (timeline-speed), and note-speed events.

### Note types: `chart/notes/`

Typed note classes (all importable from `margrete_rpc.chart.notes`):
- **Ground**: `Tap`, `Extap`, `Flick`, `Damage`
- **Long ground**: `Hold`, `Slide` — built with `add_step()`/`add_ctrl()` or `with_step()`/`with_ctrl()` (returns copy)
- **Air**: `Air`, `AirHold`, `AirSlide`
- **Air long**: `AirCrush` — carries `h`, `color`, `gap`
- **Raw**: `RawNote` / `R` — direct protobuf tree; used for unsupported structures

Long notes (Hold, Slide, AirCrush, AirSlide, AirHold) share a joint builder pattern. An `Air` note can be attached to any `_AirAttachable` long note (Hold, Slide) via the `.air` property.

### Timing: `chart/time.py`

All timing is in **ticks** (`TICKS_PER_BEAT = 1920` ticks/quarter-note). Two conversions:
- `t2p(tick)` → `Position(bar, beat, offset)` (zero-based, offset within beat)
- `p2t(bar, beat, offset)` → int tick

Inside an `EditTransaction` context, a `TickResolver` is installed via a `contextvars.ContextVar`, so note constructors accept bare `(bar, beat, offset)` tuples for `t` without threading `beat_events` everywhere. Outside a transaction, 4/4 is assumed.

`IntervalLike = (numerator, denominator)` beat fractions are accepted anywhere a tick count is expected (e.g. `gap=(1, 16)` for a 1/16th note).

### Diff system: `chart/diff.py`

When `scan=True` (the default), `open_edit` captures a baseline snapshot on entry. On exit, `build_apply_edit_request` compares the final chart against the snapshot and sends only changed notes/events (upserts + deletes). If nothing changed, `None` is returned and no request is sent. With `replace_all=True` the entire chart is replaced.

Note identity across a scan uses the note's server-assigned `_id`. Notes created inside the transaction have no id; the server assigns one when they are applied.

### Transport: `_socket.py` / `_transport.py`

The wire protocol wraps protobuf `Envelope` messages in a length-prefixed frame (4-byte big-endian length header). `SocketRpcClient` handles framing over a TCP socket. The `RpcTransport` ABC allows injecting a fake transport in tests (see `test_client_transaction.py`).

## Key invariants

- `TICKS_PER_BEAT = 1920` — all tick arithmetic must be exact integers; `d2t` raises if the fraction doesn't land on a whole tick.
- `undo()` has a known bug: undoing a transaction that **deleted** notes re-creates them in a duplicated state. Prefer designs that add/modify rather than relying on undo to reverse deletions.
- The generated protobuf files in `src/margrete_rpc/_proto/` are committed and must not be regenerated manually — they come from `proto/margrete/rpc/v1/messages.proto` but the Python generation step is not wired into the SDK build.

## Development Notes

- Follow conventional commit style: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
- The project is not yet published, so cleaner implementation and future maintainability are prioritized over backward compatibility.
