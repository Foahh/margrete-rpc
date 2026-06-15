# Margrete RPC

**Margrete RPC** is a Margrete plugin + client Python SDK that let you script **charting**.

## Motivation

Existing tooling (including my earlier project, [margrete-air-curve-converter](https://github.com/Foahh/margrete-air-curve-converter)) can be useful for
specific transforms, but it can also feel brittle when you want to:

- generate / adjust **complex pattern**
- apply **chart edits** programmatically
- iterate quickly with small patterns instead of manual editing
- leverage agentic charting using Codex / Claude Code

## Core repository content

- **[`plugin/`](plugin/)**: the Margrete plugin that hosts the RPC server  

- **[`sdk/`](sdk/)**: Python client controlling the Margrete plugin 

## Usage

Invoke the plugin command once in Margrete to start the server. Invoke it again to stop the server.

Default server config `margrete-rpc.ini`:

```ini
[server]
host = 127.0.0.1
port = auto
```

By default, the plugin binds to `127.0.0.1`. Set `host` to another IPv4 address only when you intentionally want to accept connections on that interface. For example, `0.0.0.0` accepts connections on all IPv4 interfaces and may expose the RPC server to other machines on your network.

`port = auto` asks Windows for a free local port, so multiple Margrete processes can run the plugin at the same time. Set `port` to a fixed numeric value only when you need a stable endpoint.

Logs are written per instance under:

```text
%LOCALAPPDATA%\MargreteRPC\logs\margrete-rpc-{instance_id}.log
```

## Limitation

The Margrete plugin SDK currently **does not support iterating through events by index**.

Events like `scroll speed change` are scanned from tick `0` to `last_note_tick`.

This method is very inefficient, but I have to do it until the SDK supports event iteration.

Event scan limits are set by the request (see `event_scan_extra_tick` / `event_scan_til` in the SDK).
