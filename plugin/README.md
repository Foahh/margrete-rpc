# Margrete RPC Plugin

This plugin hosts a localhost TCP/protobuf server for chart scripting.

Invoke the plugin command once in Margrete to start the server. Invoke it again to stop the server.

Default server config:

```ini
[server]
host = 127.0.0.1
port = 48731
log = margrete-rpc.log

[chart_editing]
event_scan_extra_ticks = 768000
max_scan_til = 16384
```

The plugin binds only to `127.0.0.1`.

`open_edit()` snapshots events by probing Margrete event lookup APIs from tick
0 through `min(last_note_tick + event_scan_extra_ticks, max_scan_til)`. Event
edits are fully reconciled inside that range; later events are left unchanged.
