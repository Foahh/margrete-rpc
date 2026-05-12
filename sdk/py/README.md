# margrete-rpc Python SDK

Connects Python scripts to the Margrete RPC plugin.

```python
from margrete_rpc import Margrete
from margrete_rpc.chart import Tap

mg = Margrete("127.0.0.1:48731")
tick = mg.current_tick()

with mg.transaction("add tap") as chart:
    chart.append(Tap(tick=tick, lane=4, width=1))
```

The SDK sends one append transaction when the `with` block exits successfully. If Python raises inside the block, no request is sent.
