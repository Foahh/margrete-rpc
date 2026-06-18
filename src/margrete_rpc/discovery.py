from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from margrete_rpc._endpoint import create_transport
from margrete_rpc._pipe import display_pipe_endpoint
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.errors import MargreteDiscoveryError, MargreteError
from margrete_rpc.trace import NoopTracer


@dataclass(frozen=True)
class MargreteTransportEndpoint:
    """A connection endpoint advertised by a Margrete RPC instance."""

    type: str
    endpoint: str


@dataclass(frozen=True)
class MargreteInstance:
    """A discovered Margrete RPC server, read from its discovery record.

    Attributes:
        instance_id: Identifier used to select this instance.
        endpoint: Preferred endpoint to connect to. Legacy records use ``host:port``;
            newer records may use ``npipe://./pipe/name``.
        transports: All advertised endpoints, in discovery preference order.
        pid: Host process id, if recorded.
        plugin_version: Plugin version that wrote the record, if recorded.
        log: Path to the instance's log file, if recorded.
        record_path: Path to the discovery JSON file this instance was loaded from.
    """

    instance_id: str
    endpoint: str
    transports: tuple[MargreteTransportEndpoint, ...] = ()
    pid: int | None = None
    plugin_version: str | None = None
    log: str | None = None
    record_path: Path | None = None


def discovery_dir() -> Path:
    """Return the directory where running plugins write their discovery records.

    Uses ``%LOCALAPPDATA%\\MargreteRPC\\instances`` when available, else a temp-dir
    fallback.
    """
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "MargreteRPC" / "instances"
    return Path(tempfile.gettempdir()) / "MargreteRPC" / "instances"


def list_instances(*, validate: bool = True, timeout: float = 1.0) -> list[MargreteInstance]:
    """List Margrete RPC instances advertised in the discovery directory.

    Args:
        validate: Ping each instance and drop any that do not respond.
        timeout: Per-instance ping timeout in seconds when validating.

    Returns:
        The discovered instances (only reachable ones when ``validate`` is true).
    """
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
    """Resolve a connectable endpoint via discovery.

    Args:
        instance_id: Select a specific instance by id; when ``None``, auto-detect the sole
            running instance.
        timeout: Per-instance ping timeout in seconds.

    Returns:
        The reachable instance's preferred endpoint.

    Raises:
        MargreteDiscoveryError: If the named instance is missing or unreachable, or if zero
            (or more than one) instances are found during auto-detection.
    """
    if instance_id is not None:
        for instance in list_instances(validate=False):
            if instance.instance_id != instance_id:
                continue
            validated = _validated(instance, timeout)
            if validated is None:
                raise MargreteDiscoveryError(
                    f"Margrete RPC instance {instance_id!r} is not reachable"
                )
            return validated.endpoint
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
        raw_data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw_data, dict):
        return None
    data = cast(dict[str, object], raw_data)

    instance_id = _string(data.get("instance_id"))
    if not instance_id:
        return None
    transports = _load_transports(data)
    legacy_endpoint = _string(data.get("endpoint"))
    if not transports and legacy_endpoint:
        transports = (MargreteTransportEndpoint("tcp", legacy_endpoint),)
    if not transports:
        return None
    endpoint = transports[0].endpoint

    return MargreteInstance(
        instance_id=instance_id,
        endpoint=endpoint,
        transports=transports,
        pid=_int_or_none(data.get("pid")),
        plugin_version=_string(data.get("plugin_version")),
        log=_string(data.get("log")),
        record_path=path,
    )


def _validated(instance: MargreteInstance, timeout: float) -> MargreteInstance | None:
    reachable: list[MargreteTransportEndpoint] = []
    for transport in instance.transports or (MargreteTransportEndpoint("tcp", instance.endpoint),):
        if _can_ping(transport.endpoint, timeout):
            reachable.append(transport)
    if not reachable:
        return None
    endpoint = reachable[0].endpoint
    return MargreteInstance(
        instance_id=instance.instance_id,
        endpoint=endpoint,
        transports=tuple(reachable),
        pid=instance.pid,
        plugin_version=instance.plugin_version,
        log=instance.log,
        record_path=instance.record_path,
    )


def _can_ping(endpoint: str, timeout: float) -> bool:
    client = create_transport(endpoint, timeout, NoopTracer())
    try:
        _response = client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))
    except MargreteError:
        return False
    except OSError:
        return False
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            close()
    return True


def _load_transports(data: dict[str, object]) -> tuple[MargreteTransportEndpoint, ...]:
    raw = data.get("transports")
    if not isinstance(raw, list):
        return ()
    transports: list[MargreteTransportEndpoint] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        transport = cast(dict[str, object], item)
        transport_type = _string(transport.get("type"))
        endpoint = _string(transport.get("endpoint"))
        path = _string(transport.get("path"))
        if transport_type == "tcp" and endpoint:
            transports.append(MargreteTransportEndpoint("tcp", endpoint))
        elif transport_type in {"npipe", "pipe"} and path:
            transports.append(MargreteTransportEndpoint("npipe", display_pipe_endpoint(path)))
    return tuple(transports)


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None
