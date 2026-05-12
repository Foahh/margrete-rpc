from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import Chart, normalize_event_operations


def _extend_events(request, chart: Chart) -> None:
    events = normalize_event_operations(chart)
    request.bpm_events.extend(event.to_proto() for event in events.bpm_events)
    request.beat_change_events.extend(event.to_proto() for event in events.beat_change_events)
    request.timeline_speed_events.extend(event.to_proto() for event in events.timeline_speed_events)
    request.note_speed_events.extend(event.to_proto() for event in events.note_speed_events)


def _has_existing_note_id(notes) -> bool:
    for note in notes:
        if note.id is not None or _has_existing_note_id(note.children):
            return True
    return False


@dataclass
class EditTransaction:
    name: str
    transport: object
    current_tick: int
    chart: Chart
    event_scan_until_tick: int
    event_scan_timeline_ids: list[int]

    def __enter__(self) -> EditTransaction:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            return False
        request = messages_pb2.ApplyEditPatchRequest(name=self.name)
        request.event_scan_until_tick = self.event_scan_until_tick
        request.event_scan_timeline_ids.extend(self.event_scan_timeline_ids)
        request.notes.extend(note.to_proto() for note in self.chart.notes)
        _extend_events(request, self.chart)
        self.transport.request(messages_pb2.Envelope(apply_edit_patch_request=request))
        return False


@dataclass
class AppendTransaction:
    name: str
    transport: object
    current_tick: int
    chart: Chart

    def __enter__(self) -> AppendTransaction:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            return False
        if _has_existing_note_id(self.chart.notes):
            raise ValueError("append transactions cannot send existing note ids")
        request = messages_pb2.ApplyAppendPatchRequest(name=self.name)
        request.notes.extend(note.to_proto() for note in self.chart.notes)
        _extend_events(request, self.chart)
        self.transport.request(messages_pb2.Envelope(apply_append_patch_request=request))
        return False
