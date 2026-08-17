from __future__ import annotations

import os
import re
from dataclasses import dataclass

from margrete_rpc._proto import messages_pb2
from margrete_rpc._rpc.endpoint import create_transport
from margrete_rpc.errors import MargreteDiscoveryError
from margrete_rpc.trace import NoopTracer

_PIPE_DIR = r"\\.\pipe"
_INSTANCE_RE = re.compile(r"^(?:margrete-)?(\d{4})$")
_PIPE_NAME_RE = re.compile(r"^margrete-(\d{4})$")


@dataclass(frozen=True)
class MargreteInstance:
    """A running Margrete RPC server discovered from its named pipe.

    Attributes:
        instance_id: Four-digit code used to select this instance (``0421``).
        pipe_name: Windows pipe name (``margrete-0421``).
    """

    instance_id: str
    pipe_name: str


def pipe_name_for(instance: str) -> str:
    """Normalize ``0421`` or ``margrete-0421`` to a pipe name.

    Raises:
        ValueError: If ``instance`` is not a four-digit code or ``margrete-XXXX``.
    """
    match = _INSTANCE_RE.fullmatch(instance.strip())
    if match is None:
        raise ValueError("instance must look like 0421 or margrete-0421")
    return f"margrete-{match.group(1)}"


def list_pipe_names() -> list[str]:
    """Return ``margrete-XXXX`` names currently listed under ``\\\\.\\pipe``."""
    try:
        names = os.listdir(_PIPE_DIR)
    except OSError:
        return []
    return sorted(name for name in names if _PIPE_NAME_RE.fullmatch(name))


def list_instances(*, validate: bool = True, timeout: float = 1.0) -> list[MargreteInstance]:
    """List running Margrete RPC instances by enumerating named pipes.

    Args:
        validate: Ping each instance and drop any that do not respond.
        timeout: Per-instance ping timeout in seconds when validating.

    Returns:
        The discovered instances (only reachable ones when ``validate`` is true).
    """
    instances: list[MargreteInstance] = []
    for pipe_name in list_pipe_names():
        instance = MargreteInstance(instance_id=pipe_name[-4:], pipe_name=pipe_name)
        if validate and not _can_ping(pipe_name, timeout):
            continue
        instances.append(instance)
    return instances


def resolve_pipe_name(instance: str | None = None, *, timeout: float = 1.0) -> str:
    """Resolve a ``margrete-XXXX`` pipe name.

    Args:
        instance: ``0421`` or ``margrete-0421`` to select a specific instance.
            When ``None``, auto-detect the sole running instance.
        timeout: Per-instance ping timeout in seconds during auto-detection.

    Returns:
        The pipe name to connect to.

    Raises:
        MargreteDiscoveryError: If auto-detection finds zero or multiple instances.
        ValueError: If ``instance`` is not a valid four-digit name.
    """
    if instance is not None:
        return pipe_name_for(instance)

    instances = list_instances(validate=True, timeout=timeout)
    if not instances:
        raise MargreteDiscoveryError("no running Margrete RPC server found")
    if len(instances) > 1:
        choices = ", ".join(item.pipe_name for item in instances)
        raise MargreteDiscoveryError(
            "multiple Margrete RPC servers found; pass 0421 or margrete-0421 "
            f"to select one ({choices})"
        )
    return instances[0].pipe_name


def _can_ping(pipe_name: str, timeout: float) -> bool:
    client = create_transport(pipe_name, timeout, NoopTracer())
    try:
        client.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))
    except Exception:
        return False
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            close()
    return True
