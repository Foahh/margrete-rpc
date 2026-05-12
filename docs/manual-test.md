# Manual Test

1. Build the plugin in Debug or Release.
2. Copy `margrete_rpc.dll` and `margrete-rpc.ini` into the Margrete plugin folder (use the files from your CMake build output directory, e.g. `plugin/build/Debug/` on Windows).
3. Start Margrete and invoke the **Margrete RPC** plugin command.
4. From `sdk/`, install the SDK:

```powershell
python -m pip install -e .
```

5. Run this script:

```python
from margrete_rpc import Margrete
from margrete_rpc.chart import Tap

mg = Margrete("127.0.0.1:48731")
tick = mg.current_tick()

with mg.transaction("manual tap") as chart:
    chart.append(Tap(tick=tick, lane=4, width=1))
```

6. Confirm one tap appears at the current tick.
7. Confirm Margrete undo removes the tap in one step.
8. Invoke the plugin command again and confirm the server stops.
