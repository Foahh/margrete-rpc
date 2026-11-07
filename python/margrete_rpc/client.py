from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING

from margrete_rpc._proto import messages_pb2
from margrete_rpc._rpc.endpoint import create_transport
from margrete_rpc._rpc.transport import RpcTransport
from margrete_rpc._version import ensure_compatible_api_version
from margrete_rpc.discovery import resolve_pipe_name
from margrete_rpc.trace import NoopTracer, Tracer

if TYPE_CHECKING:
    from margrete_rpc.transaction import EditTransaction


@dataclass(frozen=True)
class ServerStatus:
    """Snapshot of a running Margrete RPC server, returned by :meth:`Margrete.status`.

    Attributes:
        server_version: Plugin version string.
        server_build_time: Build timestamp of the plugin.
        instance_id: Four-digit instance code (``0421``), used to target this
            Margrete window when more than one is running.
        uptime: Seconds the server has been running.
        pid: Process id of the host Margrete process.
        log_path: Absolute path to the plugin's log file.
        config_path: Absolute path to the plugin's configuration file.
        api_version: RPC API compatibility version reported by the plugin.
    """

    server_version: str
    server_build_time: str
    instance_id: str
    uptime: int
    pid: int
    log_path: str
    config_path: str
    api_version: int


class Margrete:
    """Client for a running Margrete RPC server.

    Use ``with Margrete() as mg`` to close the connection on exit, and
    ``with mg.open_edit() as tx`` to edit ``tx.chart``.
    """

    def __init__(
        self,
        instance: str | None = None,
        *,
        timeout: float = 60.0,
        transport: RpcTransport | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        """Connect and check that the plugin's RPC API version matches this client.

        With no arguments the single running instance is auto-detected from named
        pipes named ``margrete-XXXX``. If more than one Margrete window is open, pass
        the four-digit code shown in the plugin dialog (``Margrete("0421")``).

        Args:
            instance: ``0421`` or ``margrete-0421`` to connect to that named pipe.
                Omit to auto-detect the sole running instance. Mutually exclusive
                with ``transport``.
            timeout: Seconds allowed separately for connecting and for sending a request
                and reading its response. Each auto-detection probe uses
                ``min(timeout, 1.0)`` for these limits. Ignored with ``transport``.
            transport: Pre-built transport, typically for testing. It receives the initial
                status request and is closed with the client if it provides ``close()``.
                Cannot be combined with ``instance``.
            tracer: Optional tracer for observability spans; defaults to a no-op.

        Raises:
            ValueError: If ``instance`` is not a four-digit name, or if ``instance``
                is combined with ``transport``.
            MargreteDiscoveryError: If auto-detection cannot resolve a unique instance.
            MargreteVersionError: If the plugin RPC API and Python client are not
                compatible.
        """
        self._tracer = tracer if tracer is not None else NoopTracer()
        if transport is not None:
            if instance is not None:
                raise ValueError("instance cannot be used with transport")
            self._transport = transport
        else:
            pipe_name = resolve_pipe_name(instance, timeout=min(timeout, 1.0))
            self._transport = create_transport(pipe_name, timeout, self._tracer)

        try:
            status = self.status()
            ensure_compatible_api_version(status.api_version, server_version=status.server_version)
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> Margrete:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Call the transport's ``close()`` if available.

        The default pipe transport reconnects if another request is made later.
        """
        close = getattr(self._transport, "close", None)
        if close is not None:
            close()

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
            server_version=status.server_version,
            server_build_time=status.server_build_time,
            instance_id=status.instance_id,
            uptime=status.uptime,
            pid=status.pid,
            log_path=status.log_path,
            config_path=status.config_path,
            api_version=status.api_version,
        )

    def undo(self) -> bool:
        """Undo the latest edit in Margrete's history, including edits made in the UI.

        After a successful undo, the plugin removes duplicate root-note IDs.

        Returns:
            ``True`` on success; ``False`` if undo is unavailable or Margrete rejects it.
        """
        with self._tracer.span("margrete.client.undo"):
            response = self._transport.request(
                messages_pb2.Envelope(undo_request=messages_pb2.UndoRequest())
            )
        return response.undo_response.success

    def redo(self) -> bool:
        """Redo the edit most recently undone, then remove duplicate root-note IDs.

        Returns:
            ``True`` on success; ``False`` if redo is unavailable or Margrete rejects it.
        """
        with self._tracer.span("margrete.client.redo"):
            response = self._transport.request(
                messages_pb2.Envelope(redo_request=messages_pb2.RedoRequest())
            )
        return response.redo_response.success

    def current_tick(self) -> int:
        """Return the playhead position in the editor, in ticks from the chart start.

        Returns:
            The current tick (``TICK_RESOLUTION`` ticks per whole note).
        """
        with self._tracer.span("margrete.client.current_tick"):
            response = self._transport.request(
                messages_pb2.Envelope(current_tick_request=messages_pb2.CurrentTickRequest())
            )
        return response.current_tick_response.current_tick

    def open_edit(
        self,
        *,
        event_scan_lookahead_ticks: int | None = None,
        event_scan_til_ids: list[int] | None = None,
        snapshot: bool = True,
        raw_notes: bool = False,
        replace_all_notes: bool = False,
        replace_all_events: bool = False,
    ) -> EditTransaction:
        """Load the current chart for an edit context.

        Use ``with mg.open_edit() as tx:`` and mutate ``tx.chart`` inside the block.
        Normal exit submits one undoable edit; an exception in the block skips
        submission. With the default options, an unchanged chart sends no edit request.

        The plugin applies the request to the document active at submission time.
        Keep that document open and avoid concurrent edits while the block runs.

        Args:
            event_scan_lookahead_ticks: Extend event scanning beyond the last note tick
                by this amount. ``None`` or a non-positive value uses 19200 ticks.
            event_scan_til_ids: Timelines to scan for timeline-speed events. ``None`` scans
                timelines 0-15 used by notes; ``[]`` scans all 0-15. A nonempty list scans
                those IDs regardless of note usage. Scanning runs only with ``snapshot=True``.
            snapshot: Load notes and scanned events, then diff edits against a baseline
                captured on context entry. If false, start with empty lists, append new
                notes, and upsert supplied events; existing note IDs are rejected unless
                ``replace_all_notes=True``. Without loaded beat events, tuple positions
                use 4/4; use absolute ticks when the chart's meter is unknown.
            raw_notes: Load all notes as :class:`RawNote` trees. Otherwise, use typed
                objects where supported and raw trees for unsupported structures.
            replace_all_notes: Recreate all chart notes from ``tx.chart.notes``, discarding
                their IDs. Event lists are upserted; removing events also requires
                ``replace_all_events=True``.
            replace_all_events: Delete only events captured in the baseline, then upsert
                the final event lists. Requires ``snapshot=True``.

        Returns:
            An :class:`~margrete_rpc.transaction.EditTransaction` to enter immediately.
        """
        from margrete_rpc.chart import Chart
        from margrete_rpc.transaction import EditTransaction

        tx_type = "edit_raw_notes" if raw_notes else "edit"
        with self._tracer.span("margrete.tx.begin", attrs={"tx.type": tx_type}):
            req = messages_pb2.BeginEditRequest(snapshot=snapshot)
            if event_scan_lookahead_ticks is not None:
                req.event_scan_lookahead_ticks = event_scan_lookahead_ticks
            if event_scan_til_ids is not None:
                req.event_scan_til_ids.CopyFrom(
                    messages_pb2.EventScanTilIds(ids=event_scan_til_ids)
                )
            response = self._transport.request(messages_pb2.Envelope(begin_edit_request=req))
        begin = response.begin_edit_response
        chart = Chart.from_begin_edit_response(begin, raw_notes=raw_notes)
        return EditTransaction(
            transport=self._transport,
            current_tick=begin.current_tick,
            chart=chart,
            snapshot_enabled=begin.snapshot,
            tracer=self._tracer,
            tx_type=tx_type,
            replace_all_notes=replace_all_notes,
            replace_all_events=replace_all_events,
        )
