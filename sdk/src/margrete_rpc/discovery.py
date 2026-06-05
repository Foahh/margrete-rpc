from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from margrete_rpc.errors import MargreteDiscoveryError, MargreteError
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient


@dataclass(frozen=True)
class MargreteInstance:
    instance_id: str
    endpoint: str
    pid: int | None = None
    plugin_version: str | None = None
    log: str | None = None
    record_path: Path | None = None


def discovery_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "MargreteRPC" / "instances"
    return Path(tempfile.gettempdir()) / "MargreteRPC" / "instances"


def list_instances(*, validate: bool = True, timeout: float = 1.0) -> list[MargreteInstance]:
    instances: list[MargreteInstance] = []
    directory = discovery_dir()
    if not directory.exists():
        return instances

    for path in sorted(directory.glob("*.json")):
        instance = _load_instance(path)
        if instance is None:
            continue
        if validate:
            instance = _validated(instance, timeout)
            if instance is None:
                continue
        instances.append(instance)
    return instances


def resolve_endpoint(instance_id: str | None = None, *, timeout: float = 1.0) -> str:
    if instance_id is not None:
        for instance in list_instances(validate=False):
            if instance.instance_id != instance_id:
                continue
            if _validated(instance, timeout) is None:
                raise MargreteDiscoveryError(
                    f"Margrete RPC instance {instance_id!r} is not reachable"
                )
            return instance.endpoint
        raise MargreteDiscoveryError(f"Margrete RPC instance {instance_id!r} was not found")

    instances = list_instances(validate=True, timeout=timeout)
    if not instances:
        raise MargreteDiscoveryError("no running Margrete RPC server found")
    if len(instances) > 1:
        choices = ", ".join(f"{item.instance_id}={item.endpoint}" for item in instances)
        raise MargreteDiscoveryError(
            "multiple Margrete RPC servers found; pass instance_id or endpoint "
            f"to select one ({choices})"
        )
    return instances[0].endpoint


def _load_instance(path: Path) -> MargreteInstance | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    instance_id = _string(data.get("instance_id"))
    endpoint = _string(data.get("endpoint"))
    if not instance_id or not endpoint:
        return None

    return MargreteInstance(
        instance_id=instance_id,
        endpoint=endpoint,
        pid=_int_or_none(data.get("pid")),
        plugin_version=_string(data.get("plugin_version")),
        log=_string(data.get("log")),
        record_path=path,
    )


def _validated(instance: MargreteInstance, timeout: float) -> MargreteInstance | None:
    try:
        _response = SocketRpcClient(instance.endpoint, timeout=timeout).request(
            messages_pb2.Envelope(ping_request=messages_pb2.PingRequest())
        )
    except MargreteError:
        return None
    except OSError:
        return None
    return MargreteInstance(
        instance_id=instance.instance_id,
        endpoint=instance.endpoint,
        pid=instance.pid,
        plugin_version=instance.plugin_version,
        log=instance.log,
        record_path=instance.record_path,
    )


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
