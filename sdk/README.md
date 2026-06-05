# margrete-rpc Python SDK

Python client for the **Margrete RPC** plugin.

## Requirements

- Python **3.12+**
- A running Margrete RPC server

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

mg = Margrete()
name = mg.status()
print(name)
```

`Margrete()` connects automatically when exactly one live plugin server is discovered.
If multiple Margrete instances are running the plugin, select one explicitly:

```python
from margrete_rpc import Margrete, list_instances

for instance in list_instances():
    print(instance.instance_id, instance.endpoint)

mg = Margrete(instance_id="...")
```

You can still connect to a fixed endpoint:

```python
mg = Margrete("127.0.0.1:48731")
```

## Chart Editing

```python
from margrete_rpc import BpmEvent, M, Margrete, Tap

mg = Margrete()

with mg.open_edit("move notes") as tx:
    tx.chart.notes[0].x += 1
    tx.chart.mg_notes.append(M.tap(tx.current_tick, 0, 1))
    tx.chart.events.bpm.append(BpmEvent(tick=0, bpm=180.0))

with mg.open_edit("append pattern", scan=False) as tx:
    tx.chart.notes.append(Tap(tx.current_tick, 4, 1))

with mg.open_edit("raw edit", raw=True) as tx:
    tx.chart.mg_notes[0].x += 1
```

`open_edit()` fetches the current chart and the current tick by default.

Due to the limitation of plugin, see [`plugin/README.md`](../plugin/README.md), if you just want adding notes and events, use `open_edit(scan=False)`.

Use `open_edit(raw=True)` to work entirely with raw `MgNote` trees (`MgChart`) instead of wrapped note types.

See [`example`](example/) for more complex usage.

## Chart position (`t2p` / `p2t`)

Convert absolute ticks to bar/beat/offset (and back), including time signature changes from `BeatEvent` data:

```python
from margrete_rpc import Margrete, p2t, t2p

with Margrete().open_edit("...") as tx:
    p = t2p(tx.current_tick)       # (bar, beat, offset) — beat events from context
    tick = p2t(*p)
    tick = p2t(0, 2, 0)           # bar, beat, offset
```

Outside a transaction, pass `beat_events` explicitly:

```python
from margrete_rpc import p2t, t2p

p = t2p(960, beat_events=chart.events.beat)
tick = p2t(*p, beat_events=chart.events.beat)
```

| API | Meaning |
|-----|---------|
| `b2t` / `beats_to_ticks` | Fractional beat tuple -> tick offset within one beat |
| `t2p` / `p2t` | Absolute tick <-> `(bar, beat, offset)` with measures and time signatures |

## Client: `Margrete`

```python
from margrete_rpc import Margrete
```

- `Margrete(endpoint=None, *, instance_id=None, timeout=60.0)`
- `status() -> ServerStatus`
- `undo() -> bool`
- `redo() -> bool`
- `current_tick() -> int`
- `open_edit(name: str, *, scan: bool = True, raw: bool = False, ...) -> EditTransaction`

Discovery helpers:

- `list_instances(validate=True) -> list[MargreteInstance]`
- `MargreteInstance.instance_id`
- `MargreteInstance.endpoint`

The wire schema lives in the repository `proto/` tree (`margrete.rpc.v1`).

## Errors

```python
from margrete_rpc import MargreteProtocolError, MargreteRemoteError
```

- `MargreteProtocolError`: socket/framing/request-id problems
- `MargreteRemoteError`: plugin returned an `ErrorResponse` (has `code` and message)
