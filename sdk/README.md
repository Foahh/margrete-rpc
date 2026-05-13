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
print(name)
```

## Chart Editing

```python
from margrete_rpc import BpmEvent, L, Margrete, Tap

mg = Margrete()

with mg.open_edit("move notes") as tx:
    tx.chart.notes[0].x += 1
    tx.chart.raw_notes.append(L.tap(tx.current_tick, 0, 1))
    tx.chart.events.bpm.append(BpmEvent(tick=0, bpm=180.0))

with mg.open_edit("append pattern", scan=False) as tx:
    tx.chart.notes.append(Tap(tx.current_tick, 4, 1))

with mg.open_edit("raw edit", raw_only=True) as tx:
    tx.chart.raw_notes[0].x += 1
```

`open_edit()` fetches the current chart and the current tick by default.

Due to the limitation of plugin, see [`plugin/README.md`](../plugin/README.md), if you just want adding notes and events, use `open_edit(scan=False)`.

Use `open_edit(raw_only=True)` to work entirely with raw `LLNote` trees (`LLChart`) instead of wrapped note types.

See [`example`](example/) for more complex usage.

## Client: `Margrete`

```python
from margrete_rpc import Margrete
```

- `Margrete(endpoint="127.0.0.1:48731", timeout=60.0)`
- `ping() -> str`
- `open_edit(name: str, *, scan: bool = True, raw_only: bool = False, ...) -> EditTransaction`

The wire schema lives in the repository `proto/` tree (`margrete.rpc.v1`).

## Errors

```python
from margrete_rpc import MargreteProtocolError, MargreteRemoteError
```

- `MargreteProtocolError`: socket/framing/request-id problems
- `MargreteRemoteError`: plugin returned an `ErrorResponse` (has `code` and message)
