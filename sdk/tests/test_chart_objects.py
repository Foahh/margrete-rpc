"""Chart value-model tests (Task 2 Step 1)."""

from margrete_rpc import (
    BeatChangeEvent,
    BpmEvent,
    Chart,
    Direction,
    ExAttr,
    LongAttr,
    Note,
    NoteSpeedEvent,
    NoteType,
    TimelineSpeedEvent,
)
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import _last_by_key, normalize_event_operations


def test_enum_values_match_generated_proto_numbers():
    assert int(NoteType.UNKNOWN) == messages_pb2.NOTE_TYPE_UNKNOWN
    assert int(NoteType.TAP) == messages_pb2.NOTE_TYPE_TAP
    assert int(LongAttr.NONE) == messages_pb2.LONG_ATTR_NONE
    assert int(Direction.UP) == messages_pb2.DIRECTION_UP
    assert int(ExAttr.INVERT) == messages_pb2.EX_ATTR_INVERT


def test_note_tap_factory_defaults():
    n = Note.tap(960, x=12)
    assert n.type == NoteType.TAP
    assert n.long_attr == LongAttr.NONE
    assert n.direction == Direction.NONE
    assert n.ex_attr == ExAttr.NONE
    assert n.tick == 960
    assert n.x == 12
    assert n.width == 1
    assert n.height == 1
    assert n.timeline_id == 0
    assert n.variation_id == 0
    assert n.option_value == 0
    assert n.children == []
    assert n.id is None


def test_note_from_proto_optional_id_and_nested_children():
    inner = messages_pb2.Note(type=messages_pb2.NOTE_TYPE_AIR, tick=1000)
    pb = messages_pb2.Note(
        id=42,
        type=messages_pb2.NOTE_TYPE_HOLD,
        long_attr=messages_pb2.LONG_ATTR_BEGIN,
        direction=messages_pb2.DIRECTION_LEFT,
        ex_attr=messages_pb2.EX_ATTR_HAS_NOTE,
        variation_id=3,
        x=7,
        width=2,
        height=10,
        tick=880,
        timeline_id=1,
        option_value=99,
        children=[inner],
    )
    note = Note.from_proto(pb)

    assert note.id == 42
    assert note.type == NoteType.HOLD
    assert note.long_attr == LongAttr.BEGIN
    assert note.direction == Direction.LEFT
    assert note.ex_attr == ExAttr.HAS_NOTE
    assert note.variation_id == 3
    assert note.x == 7
    assert note.width == 2
    assert note.height == 10
    assert note.tick == 880
    assert note.timeline_id == 1
    assert note.option_value == 99
    assert len(note.children) == 1
    assert note.children[0].type == NoteType.AIR


def test_note_to_proto_preserves_optional_id_and_children_roundtrip():
    original = messages_pb2.Note(
        id=5,
        type=messages_pb2.NOTE_TYPE_SLIDE,
        tick=10,
        x=3,
        children=[messages_pb2.Note(type=messages_pb2.NOTE_TYPE_DAMAGE, tick=11)],
    )
    roundtrip = Note.from_proto(original).to_proto()
    assert roundtrip.SerializeToString() == original.SerializeToString()


def test_note_to_proto_omits_id_when_none():
    n = Note.tap(1, x=2)
    pb = n.to_proto()
    assert not pb.HasField("id")


def test_chart_from_begin_edit_response():
    pb = messages_pb2.BeginEditResponse(
        current_tick=12345,
        notes=[messages_pb2.Note(type=messages_pb2.NOTE_TYPE_TAP, tick=960, id=77)],
    )
    chart = Chart.from_begin_edit_response(pb)

    assert chart.current_tick == 12345
    assert len(chart.notes) == 1
    assert chart.notes[0].id == 77
    assert chart.notes[0].type == NoteType.TAP


def test_last_by_key_keeps_last_occurrence_per_key():
    assert _last_by_key([(1, "a"), (2, "b"), (1, "c")]) == {1: "c", 2: "b"}


def test_normalize_event_operations_dedupes_and_orders():
    bpms = [
        BpmEvent(tick=192, bpm=200.0),
        BpmEvent(tick=0, bpm=120.0),
        BpmEvent(tick=0, bpm=130.5),
        BpmEvent(tick=96, bpm=150.0),
    ]
    beats = [
        BeatChangeEvent(bar=2, beats_per_bar=7, beat_unit=4),
        BeatChangeEvent(bar=1, beats_per_bar=4, beat_unit=4),
        BeatChangeEvent(bar=1, beats_per_bar=5, beat_unit=8),
    ]
    timelines = [
        TimelineSpeedEvent(tick=480, timeline_id=0, speed=2.0),
        TimelineSpeedEvent(tick=0, timeline_id=1, speed=1.0),
        TimelineSpeedEvent(tick=480, timeline_id=0, speed=3.25),
        TimelineSpeedEvent(tick=480, timeline_id=1, speed=9.0),
    ]
    note_speed = [
        NoteSpeedEvent(tick=10, speed=4.0),
        NoteSpeedEvent(tick=0, speed=1.0),
        NoteSpeedEvent(tick=10, speed=8.5),
    ]

    nb, nbc, nt, nn = normalize_event_operations(bpms, beats, timelines, note_speed)

    assert nb == [
        BpmEvent(tick=0, bpm=130.5),
        BpmEvent(tick=96, bpm=150.0),
        BpmEvent(tick=192, bpm=200.0),
    ]

    assert nbc == [
        BeatChangeEvent(bar=1, beats_per_bar=5, beat_unit=8),
        BeatChangeEvent(bar=2, beats_per_bar=7, beat_unit=4),
    ]

    assert nt == [
        TimelineSpeedEvent(tick=0, timeline_id=1, speed=1.0),
        TimelineSpeedEvent(tick=480, timeline_id=0, speed=3.25),
        TimelineSpeedEvent(tick=480, timeline_id=1, speed=9.0),
    ]

    assert nn == [
        NoteSpeedEvent(tick=0, speed=1.0),
        NoteSpeedEvent(tick=10, speed=8.5),
    ]
