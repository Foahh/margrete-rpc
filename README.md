# Margrete RPC

**Margrete RPC** is a [UMIGURI/Margrete](https://umgr.inonote.jp/en/margrete) plugin plus a Python client package that lets you script **charting**.

## Documentation

For installation instructions and usage examples of this project, see:
https://mg.foahh.com

关于此项目的安装说明和使用示例请见：
https://mg.foahh.com

## Motivation

Existing tooling (including my earlier project, [margrete-air-curve-converter](https://github.com/Foahh/margrete-air-curve-converter)) can be useful for
specific transforms, but it can also feel brittle when you want to:

- generate / adjust **complex pattern**
- apply **chart edits** programmatically
- iterate quickly with small patterns instead of manual editing
- leverage agentic charting using Codex / Claude Code

## Core repository content

- **[`plugin/`](plugin/)**: Rust Margrete plugin that hosts the local protobuf RPC **server** over a Windows named pipe

- **[`python/margrete_rpc`](python/margrete_rpc)**: Python **client** controlling the Margrete plugin

- **[`proto/`](proto/)**: protobuf definitions shared by the plugin and the Python client

- **[`website/`](website/)**: Fumadocs documentation site; auto-generates API reference from the Python package
