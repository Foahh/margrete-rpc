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

mg = Margrete("127.0.0.1:48731")
print(mg.ping(), mg.current_tick())
```

6. Confirm the server responds without errors.
7. Invoke the plugin command again and confirm the server stops.
