from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc._socket import SocketRpcClient
from margrete_rpc._transport import RpcTransport
from margrete_rpc.discovery import resolve_endpoint
from margrete_rpc.trace import NoopTracer, Tracer

if TYPE_CHECKING:
    from margrete_rpc.transaction import EditTransaction


@dataclass(frozen=True)
class ServerStatus:
    """Snapshot of a running Margrete RPC server, returned by :meth:`Margrete.status`.

    Attributes:
        server_name: Human-readable name reported by the plugin.
        server_version: Plugin version string.
        server_build_time: Build timestamp of the plugin.
        instance_id: Identifier of this Margrete instance, used to target it during
            discovery (see :func:`margrete_rpc.resolve_endpoint`).
        uptime: Seconds the server has been running.
        pid: Process id of the host Margrete process.
        log_path: Absolute path to the plugin's log file.
        config_path: Absolute path to the plugin's configuration file.
    """

    server_name: str
    server_version: str
    server_build_time: str
    instance_id: str
    uptime: int
    pid: int
    log_path: str
    config_path: str


class Margrete:
    """Client for a running Margrete RPC server.

    This is the entry point of the SDK. Construct one to connect to a Margrete
    instance, then call :meth:`open_edit` to make scriptable changes to the current
    chart inside a transaction.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        *,
        instance_id: str | None = None,
        timeout: float = 60.0,
        transport: RpcTransport | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        """Connect to a Margrete RPC server.

        With no arguments the single running instance is auto-detected via discovery.

        Args:
            endpoint: Explicit ``host:port`` to connect to. Mutually exclusive with
                ``instance_id`` and ``transport``.
            instance_id: Connect to the discovered instance with this id (see
                :class:`ServerStatus.instance_id`). Mutually exclusive with ``endpoint``.
            timeout: Socket timeout in seconds for requests. Discovery uses at most
                one second of this budget.
            transport: Pre-built transport to use instead of opening a socket; intended
                for testing. Cannot be combined with ``endpoint`` or ``instance_id``.
            tracer: Optional tracer for observability spans; defaults to a no-op.

        Raises:
            ValueError: If conflicting connection arguments are supplied.
            MargreteDiscoveryError: If auto-detection cannot resolve an instance.
        """
        self._tracer = tracer if tracer is not None else NoopTracer()
        if transport is not None:
            if endpoint is not None or instance_id is not None:
                raise ValueError("endpoint and instance_id cannot be used with transport")
            self._transport = transport
        else:
            if endpoint is not None and instance_id is not None:
                raise ValueError("pass endpoint or instance_id, not both")
            if endpoint is None:
                endpoint = resolve_endpoint(instance_id, timeout=min(timeout, 1.0))
            self._transport = SocketRpcClient(endpoint, timeout, tracer=self._tracer)

    def ping(self) -> None:
        """Check connectivity by round-tripping an empty request to the server.

        Raises:
            MargreteError: If the server is unreachable or the request fails.
        """
        with self._tracer.span("margrete.client.ping"):
            self._transport.request(messages_pb2.Envelope(ping_request=messages_pb2.PingRequest()))

    def status(self) -> ServerStatus:
        """Query the server for its identity and runtime status.

        Returns:
            A :class:`ServerStatus` snapshot (version, instance id, uptime, paths).
        """
        with self._tracer.span("margrete.client.status"):
            response = self._transport.request(
                messages_pb2.Envelope(status_request=messages_pb2.StatusRequest())
            )
        status = response.status_response
        return ServerStatus(
            server_name=status.server_name,
            server_version=status.server_version,
            server_build_time=status.server_build_time,
            instance_id=status.instance_id,
            uptime=status.uptime,
            pid=status.pid,
            log_path=status.log_path,
            config_path=status.config_path,
        )

    def undo(self) -> bool:
        """Undo the last edit on the Margrete undo stack.

        Returns:
            ``True`` if an edit was undone, ``False`` if the stack was empty.

        Note:
            Undo applies to Margrete's own history, which includes edits made through
            this SDK. Undoing a transaction that deleted notes can re-create them in a
            duplicated state, so prefer designing transactions that add or modify rather
            than relying on undo to reverse deletions.
        """
        with self._tracer.span("margrete.client.undo"):
            response = self._transport.request(
                messages_pb2.Envelope(undo_request=messages_pb2.UndoRequest())
            )
        return response.undo_response.success

    def redo(self) -> bool:
        """Redo the edit most recently undone.

        Returns:
            ``True`` if an edit was redone, ``False`` if there was nothing to redo.
        """
        with self._tracer.span("margrete.client.redo"):
            response = self._transport.request(
                messages_pb2.Envelope(redo_request=messages_pb2.RedoRequest())
            )
        return response.redo_response.success

    def current_tick(self) -> int:
        """Return the playhead position in the editor, in ticks from the chart start.

        Returns:
            The current tick (``TICKS_PER_BEAT`` ticks per beat).
        """
        with self._tracer.span("margrete.client.current_tick"):
            response = self._transport.request(
                messages_pb2.Envelope(current_tick_request=messages_pb2.CurrentTickRequest())
            )
        return response.current_tick_response.current_tick

    def open_edit(
        self,
        name: str,
        *,
        event_scan_extra_tick: int | None = None,
        event_scan_til: list[int] | None = None,
        event_scan_note_til_only: bool = False,
        scan: bool = True,
        raw: bool = False,
        replace_all: bool = False,
    ) -> EditTransaction:
        """Begin an edit transaction over the current chart.

        Returns an :class:`~margrete_rpc.transaction.EditTransaction` to be used as a
        context manager. Mutate ``tx.chart`` inside the ``with`` block; on clean exit the
        changes are diffed and applied to Margrete as a single undoable edit, and on an
        exception nothing is applied.

        Args:
            name: Label for the edit, shown in Margrete's undo history.
            event_scan_extra_tick: Extra tick window to scan for timeline events beyond
                the note range; ``None`` uses the server default.
            event_scan_til: Explicit list of ticks at which to scan timeline-speed events.
            event_scan_note_til_only: Restrict timeline-speed scanning to ticks that carry
                notes.
            scan: Capture a baseline snapshot so only changed notes are sent on apply.
                Disable to skip diffing.
            raw: Load the chart as a raw protobuf-tree model (:class:`RawNote`) instead of
                typed note objects.
            replace_all: Replace every note in the chart on apply instead of applying a
                diff. Useful for full rewrites.

        Returns:
            An :class:`~margrete_rpc.transaction.EditTransaction` bound to the loaded chart.
        """
        from margrete_rpc.chart import Chart
        from margrete_rpc.transaction import EditTransaction

        tx_type = "edit_raw" if raw else "edit"
        with self._tracer.span("margrete.tx.begin", attrs={"tx.type": tx_type, "tx.name": name}):
            req = messages_pb2.BeginEditRequest(
                name=name, scan=scan, event_scan_note_til_only=event_scan_note_til_only
            )
            if event_scan_extra_tick is not None:
                req.event_scan_extra_tick = event_scan_extra_tick
            if event_scan_til is not None:
                req.event_scan_til.extend(event_scan_til)
            response = self._transport.request(messages_pb2.Envelope(begin_edit_request=req))
        begin = response.begin_edit_response
        chart = Chart.from_begin_edit_response(begin, raw=raw)
        return EditTransaction(
            name=name,
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=chart,
            scan=begin.scan,
            tracer=self._tracer,
            tx_type=tx_type,
            replace_all_notes=replace_all,
        )
