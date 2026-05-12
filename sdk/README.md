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

## Client: `Margrete`

```python
from margrete_rpc import Margrete
```

- `Margrete(endpoint="127.0.0.1:48731", timeout=5.0)`
- `ping() -> str`
- `current_tick() -> int`

The wire schema lives in the repository `proto/` tree (`margrete.rpc.v1`).

## Errors

```python
from margrete_rpc import MargreteProtocolError, MargreteRemoteError
```

- `MargreteProtocolError`: socket/framing/request-id problems
- `MargreteRemoteError`: plugin returned an `ErrorResponse` (has `code` and message)
