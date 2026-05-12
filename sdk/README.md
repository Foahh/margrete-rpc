# margrete-rpc Python SDK

Python client for the **Margrete RPC** plugin.

## Requirements

- Python **3.12+**
- A running Margrete RPC server (default listen address: `127.0.0.1:48731`)

## Installation

From the `sdk/` directory (editable install while developing):

```bash
pip install -e .
```

Or install from a path to this folder:

```bash
pip install /path/to/margrete-rpc/sdk
```

## Quick start

```python
from margrete_rpc import Margrete

mg = Margrete("127.0.0.1:48731")
name = mg.ping()
tick = mg.current_tick()
print(name, tick)
```

## Chart Editing

```python
from margrete_rpc import BpmEvent, Margrete, Note

mg = Margrete()

with mg.open_edit("move notes") as tx:
    tx.chart.notes[0].x += 1
    tx.chart.bpm_events.append(BpmEvent(tick=0, bpm=180.0))

with mg.open_append("append pattern") as tx:
    tx.chart.notes.append(Note.tap(tick=tx.current_tick, x=4, width=1))
```

`open_edit()` fetches the current note tree and commits the final note tree.
`open_append()` fetches only the current tick and appends new notes. Event lists
start empty in both modes and represent append-or-replace operations by event
key; they are not complete snapshots of existing Margrete events.

## Building notes

Use classmethods on `Note` for common kinds (all use keyword `tick`, `x`, optional `width`, plus `**kwargs` for any other `Note` field such as `direction`, `long_attr`, `children`):

- `Note.tap`, `Note.extap`, `Note.flick`, `Note.damage`
- `Note.hold`, `Note.slide` — default `long_attr=LongAttr.BEGIN` for a long-note head; pass `long_attr=` for other segments
- **Slide segments:** `Note.slide_begin`, `slide_step`, `slide_control`, `slide_curve_control`, `slide_end`, `slide_end_noact` (fixed `LongAttr` each)
- `Note.air`, `Note.air_slide`, `Note.air_hold` — generic `air_slide` / `air_hold` default `long_attr=LongAttr.BEGIN`
- **Air-slide segments:** `Note.air_slide_begin`, `air_slide_step`, `air_slide_control`, `air_slide_curve_control`, `air_slide_end`, `air_slide_end_noact`

## Client: `Margrete`

```python
from margrete_rpc import Margrete
```

- `Margrete(endpoint="127.0.0.1:48731", timeout=5.0)`
- `ping() -> str`
- `current_tick() -> int`
- `open_edit(name: str) -> EditTransaction` — context manager; snapshot note tree, commit on success
- `open_append(name: str) -> AppendTransaction` — context manager; current tick only, append-only notes

The wire schema lives in the repository `proto/` tree (`margrete.rpc.v1`).

## Errors

```python
from margrete_rpc import MargreteProtocolError, MargreteRemoteError
```

- `MargreteProtocolError`: socket/framing/request-id problems
- `MargreteRemoteError`: plugin returned an `ErrorResponse` (has `code` and message)
