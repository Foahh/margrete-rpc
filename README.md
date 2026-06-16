# Margrete RPC

**Margrete RPC** is a [UMIGURI/Margrete](https://umgr.inonote.jp/en/margrete) plugin plus a Python client package that lets you script **charting**.

## Motivation

Existing tooling (including my earlier project, [margrete-air-curve-converter](https://github.com/Foahh/margrete-air-curve-converter)) can be useful for
specific transforms, but it can also feel brittle when you want to:

- generate / adjust **complex pattern**
- apply **chart edits** programmatically
- iterate quickly with small patterns instead of manual editing
- leverage agentic charting using Codex / Claude Code

## Core repository content

- **[`plugin/`](plugin/)**: C++ Margrete plugin that hosts the TCP/protobuf RPC **server**

- **[`src/margrete_rpc`](src/margrete_rpc)**: Python **client** controlling the Margrete plugin

- **[`proto/`](proto/)**: protobuf definitions shared by the plugin and the Python client

- **[`docs/`](docs/)**: Fumadocs documentation site; auto-generates API reference from the Python package
