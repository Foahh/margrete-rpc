# Margrete RPC Plugin

This plugin hosts a localhost TCP/protobuf server for chart scripting.

Invoke the plugin command once in Margrete to start the server. Invoke it again to stop the server.

Default server config `margrete-rpc.ini`:

```ini
[server]
host = 127.0.0.1
port = 48731
log = margrete-rpc.log
```

The plugin binds only to `127.0.0.1`.

## Limitation

The Margrete plugin SDK currently **does not support iterating through events by index**.

Events like `scroll speed change` are scanned from tick `0` to `last_note_tick`.

This method is very inefficient, but I have to do it until the SDK supports event iteration.

Event scan limits are set by the request (see `event_scan_extra_tick` / `event_scan_til` in the SDK).