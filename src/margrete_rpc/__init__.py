from margrete_rpc._version import client_version as _client_version
from margrete_rpc.client import Margrete, ServerStatus
from margrete_rpc.discovery import MargreteInstance, discovery_dir, list_instances, resolve_endpoint
from margrete_rpc.errors import (
    MargreteDiscoveryError,
    MargreteError,
    MargreteProtocolError,
    MargreteRemoteError,
    MargreteTimeoutError,
    MargreteVersionError,
)
from margrete_rpc.trace import CallbackTracer, NoopTracer, TraceEvent, Tracer

__version__ = _client_version()

__all__ = [
    "CallbackTracer",
    "Margrete",
    "MargreteDiscoveryError",
    "MargreteError",
    "MargreteInstance",
    "MargreteProtocolError",
    "MargreteRemoteError",
    "MargreteTimeoutError",
    "MargreteVersionError",
    "NoopTracer",
    "ServerStatus",
    "TraceEvent",
    "Tracer",
    "__version__",
    "discovery_dir",
    "list_instances",
    "resolve_endpoint",
]
