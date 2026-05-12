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
from margrete_rpc.chart import Tap

mg = Margrete("127.0.0.1:48731")
tick = mg.current_tick()

with mg.transaction("add tap") as tx:
    tx.insert_at_tick(tick, [Tap(tick=0, lane=4, width=1)])
```

When the `with` block finishes **without** an exception, the SDK sends a single **edit transaction** containing every item you queued. If Python raises inside the block, **nothing** is sent.

## Client: `Margrete`

```python
from margrete_rpc import Margrete
```

- `Margrete(endpoint="127.0.0.1:48731", timeout=5.0)`
- `ping() -> str`
- `current_tick() -> int`
- `transaction(name: str = "Margrete RPC transaction")`

## Transactions

```python
from margrete_rpc import Margrete
from margrete_rpc.chart import Hold, Tap

mg = Margrete()

with mg.transaction("my edit") as tx:
    tx.insert_at_tick(0, [Tap(tick=0, lane=2, width=1)])
    tx.insert_at_tick(0, [Hold(tick=120, lane=2, width=2, duration=240)])
```

- `insert_at_tick(origin_tick, objects)`: shifts each object by `origin_tick` (relative ticks → absolute)
- `commit() -> int`: sends queued items now and clears the queue

If the `with` body raises, pending items are **not** committed on exit.

## Errors

```python
from margrete_rpc import MargreteProtocolError, MargreteRemoteError
```

- `MargreteProtocolError`: socket/framing/request-id problems
- `MargreteRemoteError`: plugin returned an `ErrorResponse` (has `code` and message)

## Chart Objects

Import from `margrete_rpc.chart`:

- Notes: `Tap`, `ExTap`, `Flick`, `Damage`, `Hold`, `Slide`, `Air`, `AirHold`, `AirSlide`, `AirCrush`
- Events: `BpmEvent`, `BeatEvent`, `ScrollSpeedEvent`, `NoteSpeedEvent`
- Low-level: `RawNoteNode`

Most objects support `shifted(tick_offset)`.
