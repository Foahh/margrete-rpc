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
from margrete_rpc.chart import normalize_event_operations


def test_note_type_factories_set_kind_and_geometry():
    assert Note.tap(tick=1, x=2).type is NoteType.TAP
    assert Note.extap(tick=1, x=2).type is NoteType.EXTAP
    assert Note.flick(tick=1, x=2).type is NoteType.FLICK
    assert Note.damage(tick=1, x=2).type is NoteType.DAMAGE
    assert Note.hold(tick=1, x=2).type is NoteType.HOLD
    assert Note.hold(tick=1, x=2).long_attr is LongAttr.BEGIN
    assert Note.slide_begin(tick=1, x=2).type is NoteType.SLIDE
    assert Note.slide_begin(tick=1, x=2).long_attr is LongAttr.BEGIN
    assert Note.air(tick=1, x=2).type is NoteType.AIR
    assert Note.air_slide(tick=1, x=2).type is NoteType.AIRSLIDE
    assert Note.air_hold(tick=1, x=2).type is NoteType.AIRHOLD


def test_slide_segment_factories_match_long_attr():
    assert Note.slide_begin(tick=10, x=3) == Note(
        type=NoteType.SLIDE,
        long_attr=LongAttr.BEGIN,
        tick=10,
        x=3,
        width=1,
    )
    assert Note.slide_step(tick=10, x=3).long_attr is LongAttr.STEP
    assert Note.slide_control(tick=10, x=3).long_attr is LongAttr.CONTROL
    assert Note.slide_curve_control(tick=10, x=3).long_attr is LongAttr.CURVE_CONTROL
    assert Note.slide_end(tick=10, x=3).long_attr is LongAttr.END


def test_air_slide_segment_factories_match_long_attr():
    begin = Note.air_slide_begin(tick=11, x=4)
    assert begin == Note.air_slide(tick=11, x=4, long_attr=LongAttr.BEGIN)
    assert Note.air_slide_step(tick=11, x=4).long_attr is LongAttr.STEP
    assert Note.air_slide_control(tick=11, x=4).long_attr is LongAttr.CONTROL
    assert Note.air_slide_curve_control(tick=11, x=4).long_attr is LongAttr.CURVE_CONTROL
    assert Note.air_slide_end(tick=11, x=4).long_attr is LongAttr.END
    assert Note.air_slide_end_noact(tick=11, x=4).long_attr is LongAttr.END_NOACT


def test_note_defaults_and_tap_constructor_are_pythonic():
    note = Note.tap(tick=960, x=4, width=1)

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.NONE
    assert note.direction is Direction.NONE
    assert note.ex_attr is ExAttr.NONE
    assert note.tick == 960
    assert note.x == 4
    assert note.width == 1
    assert note.id is None
    assert note.children == []


def test_note_round_trips_to_protobuf_with_children_and_id():
    note = Note(
        id=10,
        type=NoteType.SLIDE,
        long_attr=LongAttr.BEGIN,
        direction=Direction.UPLEFT,
        ex_attr=ExAttr.HAS_NOTE,
        variation_id=2,
        x=3,
        width=2,
        height=1,
        tick=120,
        timeline_id=4,
        option_value=9,
        children=[Note.tap(tick=180, x=5, width=1)],
    )

    proto = note.to_proto()
    restored = Note.from_proto(proto)

    assert proto.id == 10
    assert proto.type == messages_pb2.NOTE_TYPE_SLIDE
    assert proto.long_attr == messages_pb2.LONG_ATTR_BEGIN
    assert restored == note


def test_chart_from_begin_edit_response_keeps_events_empty():
    response = messages_pb2.BeginEditResponse(
        current_tick=240,
        notes=[messages_pb2.Note(type=messages_pb2.NOTE_TYPE_TAP, tick=240, x=1)],
    )

    chart = Chart.from_begin_edit_response(response)

    assert chart.notes == [Note(type=NoteType.TAP, tick=240, x=1)]
    assert chart.bpm_events == []
    assert chart.beat_change_events == []
    assert chart.timeline_speed_events == []
    assert chart.note_speed_events == []


def test_event_normalization_uses_last_write_wins_by_key():
    chart = Chart(
        bpm_events=[BpmEvent(0, 120.0), BpmEvent(0, 180.0)],
        beat_change_events=[
            BeatChangeEvent(bar=0, beats_per_bar=3, beat_unit=4),
            BeatChangeEvent(bar=0, beats_per_bar=4, beat_unit=4),
        ],
        timeline_speed_events=[
            TimelineSpeedEvent(tick=960, timeline_id=1, speed=0.5),
            TimelineSpeedEvent(tick=960, timeline_id=1, speed=0.75),
        ],
        note_speed_events=[NoteSpeedEvent(480, 1.5), NoteSpeedEvent(480, 1.25)],
    )

    normalized = normalize_event_operations(chart)

    assert normalized.bpm_events == [BpmEvent(0, 180.0)]
    assert normalized.beat_change_events == [BeatChangeEvent(0, 4, 4)]
    assert normalized.timeline_speed_events == [TimelineSpeedEvent(960, 1, 0.75)]
    assert normalized.note_speed_events == [NoteSpeedEvent(480, 1.25)]
