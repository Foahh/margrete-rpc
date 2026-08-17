from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_api_version(root: Path) -> int:
    text = (root / "proto" / "API_VERSION").read_text(encoding="utf-8").strip()
    return int(text)


def generate(root: Path | None = None) -> Path:
    """Compile proto/margrete/rpc/messages.proto into python/margrete_rpc/_proto/."""
    root = root or repo_root()
    proto_file = root / "proto" / "margrete" / "rpc" / "messages.proto"
    out_dir = root / "python" / "margrete_rpc" / "_proto"
    out_dir.mkdir(parents=True, exist_ok=True)

    from grpc_tools import protoc

    include = str(Path(protoc.__file__).resolve().parent / "_proto")
    args = [
        "grpc_tools.protoc",
        f"-I{root / 'proto'}",
        f"-I{include}",
        f"--python_out={out_dir}",
        f"--pyi_out={out_dir}",
        str(proto_file),
    ]
    if protoc.main(args) != 0:
        raise SystemExit(f"protoc failed: {' '.join(args)}")

    api_version = read_api_version(root)
    for package_dir in (
        out_dir,
        out_dir / "margrete",
        out_dir / "margrete" / "rpc",
    ):
        package_dir.mkdir(parents=True, exist_ok=True)
        init = package_dir / "__init__.py"
        if package_dir == out_dir:
            init.write_text(
                "from margrete_rpc._proto.margrete.rpc import messages_pb2 as messages_pb2\n"
                f"\nRPC_API_VERSION = {api_version}\n"
                '\n__all__ = ["RPC_API_VERSION", "messages_pb2"]\n',
                encoding="utf-8",
            )
        elif not init.exists():
            init.write_text("", encoding="utf-8")
    return out_dir


def main() -> None:
    generate()


if __name__ == "__main__":
    main()
    sys.exit(0)
