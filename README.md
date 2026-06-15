# Margrete RPC

**Margrete RPC** is a [UMIGURI/Margrete](https://umgr.inonote.jp/en/margrete) plugin + client Python SDK that let you script **charting**.

## Motivation

Existing tooling (including my earlier project, [margrete-air-curve-converter](https://github.com/Foahh/margrete-air-curve-converter)) can be useful for
specific transforms, but it can also feel brittle when you want to:

- generate / adjust **complex pattern**
- apply **chart edits** programmatically
- iterate quickly with small patterns instead of manual editing
- leverage agentic charting using Codex / Claude Code

## Core repository content

- **[`plugin/`](plugin/)**: the Margrete plugin that hosts the RPC server

- **[`src/margrete_rpc`](src/margrete_rpc)**: Python client controlling the Margrete plugin

- **[`proto/`](proto/)**: protobuf definitions shared by the plugin and the SDK
