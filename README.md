# Margrete RPC

**Margrete RPC** is a Margrete plugin + client SDKs that let you script **charting**.

## Motivation

Existing tooling (including my earlier project, [margrete-air-curve-converter](https://github.com/Foahh/margrete-air-curve-converter)) can be great for
specific transforms, but it can also feel brittle when you want to:

- generate / adjust **complex pattern**
- apply **chart edits** programmatically
- iterate quickly with small patterns instead of manual editing

## Repository layout

- **[`plugin/`](plugin/)**: the Margrete plugin that hosts the localhost RPC server  
  See [`plugin/README.md`](plugin/README.md) for server behavior and default configuration.
- **[`sdk/`](sdk/)**: Python client for the supported RPC calls  
  See [`sdk/README.md`](sdk/README.md) for installation and usage.
- **[`proto/`](proto/)**: protobuf schema shared by the plugin and SDKs.

## How it works (high level)

- You start the server from inside Margrete by running the plugin command.
- Your script connects to `127.0.0.1:48731` (by default).
- Supported calls are defined in [`proto/margrete/rpc/v1/messages.proto`](proto/margrete/rpc/v1/messages.proto).

## Quick start

1. **Install/enable the plugin** in Margrete.
2. In Margrete, run the plugin command once to **start** the server (run again to stop).
3. Use an SDK to call the RPC surface you need:
   - **Python**: follow [`sdk/README.md`](sdk/README.md)

## Links

- **Plugin README**: [`plugin/README.md`](plugin/README.md)
- **Python SDK README**: [`sdk/README.md`](sdk/README.md)
