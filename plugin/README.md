# Margrete RPC Plugin

This plugin hosts a localhost TCP/protobuf server for append-only chart scripting.

Invoke the plugin command once in Margrete to start the server. Invoke it again to stop the server.

Default server config:

```ini
[server]
host = 127.0.0.1
port = 48731
log = margrete-rpc.log
```

The plugin binds only to `127.0.0.1`.
