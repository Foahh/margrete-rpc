import sys
from pathlib import Path


def pytest_configure() -> None:
    proto_init = Path(__file__).resolve().parents[1] / "margrete_rpc" / "_proto" / "__init__.py"
    if proto_init.exists():
        return
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    sys.path.insert(0, str(scripts))
    from generate_proto import generate

    generate()
