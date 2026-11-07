# Margrete RPC

Margrete RPC lets Python scripts read and edit charts in
[UMIGURI/Margrete](https://umgr.inonote.jp/en/margrete). A Rust plugin runs inside
Margrete and communicates with the Python client over a local Windows named pipe.

## Documentation

See the [documentation](https://mg.foahh.com) for installation, tutorials, and the
Python API reference.

安装说明、教程和 Python API 参考请见[项目文档](https://mg.foahh.com)。

## Repository

- [`python/margrete_rpc/`](python/margrete_rpc/): client, chart models, and pattern
  utilities. Public docstrings supply the generated API reference.
- [`plugin/src/`](plugin/src/): RPC server and Margrete ABI bindings.
- [`proto/`](proto/): shared RPC schema and API compatibility version. Edit the
  schema here; Python and Rust protobuf bindings are generated during builds.
- [`examples/`](examples/): scripts for generating patterns and streaming video
  into a chart.
- [`website/`](website/): documentation site, including tutorials and generated
  API reference pages.

## Development

Use `uv` for Python development. From the repository root:

```powershell
uv run --extra dev pytest
.\format.ps1 -Check
```

Build the plugin on Windows with stable Rust, the MSVC target, and `protoc` on
`PATH`. The SDK headers in `plugin/margrete/` are a reference, not a build dependency.

```powershell
.\build.ps1 -Test
```

This runs Rust tests, then writes the release DLL and INI to `plugin/target/release/`.
Add `-Publish` to replace `publish/` with those files and the installation README.
