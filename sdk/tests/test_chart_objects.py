import pytest

from margrete_rpc import (
    AirColor,
    AirCrushColor,
    AirCrushOption,
    BeatChangeEvent,
    BpmEvent,
    Chart,
    ChartEvents,
    Direction,
    ExAttr,
    LongAttr,
    Note,
    NoteSpeedEvent,
    NoteType,
    TimelineSpeedEvent,
)
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model import normalize_event_operations


def test_note_type_factories_set_kind_and_geometry():
    assert Note.tap(1, 2, 1).type is NoteType.TAP
    assert Note.extap(1, 2, 1).type is NoteType.EXTAP
    assert Note.flick(1, 2, 1).type is NoteType.FLICK
    assert Note.damage(1, 2, 1).type is NoteType.DAMAGE
    assert Note.hold_begin(1, 2, 1).type is NoteType.HOLD
    assert Note.hold_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert Note.hold_end(1, 2, 1).long_attr is LongAttr.END
    assert Note.slide_begin(1, 2, 1).type is NoteType.SLIDE
    assert Note.slide_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert Note.air(1, 2, 1).type is NoteType.AIR
    assert Note.air_slide_begin(1, 2, 1, 80).type is NoteType.AIRSLIDE
    assert Note.air_hold_begin(1, 2, 1, 80).type is NoteType.AIRHOLD
    assert Note.air_hold_begin(1, 2, 1, 80).long_attr is LongAttr.BEGIN
    assert Note.air_hold_end(1, 2, 1, 80).long_attr is LongAttr.END
    crush0 = Note.air_crush_begin(1, 2, 1, 80, AirCrushOption.TRACELIKE)
    assert crush0.type is NoteType.AIRCRUSH
    assert crush0.long_attr is LongAttr.BEGIN
    assert crush0.option_value == AirCrushOption.TRACELIKE
    head = Note.air_crush_begin(1, 2, 1, 80, AirCrushOption.HEAD_ONLY)
    assert head.option_value == 0x7FFFFFFF
    assert Note.air_crush_begin(1, 2, 1, 80, 120).option_value == 120


def test_air_crush_color_values_match_variation_ids():
    assert AirCrushColor.DEF == 0
    assert AirCrushColor.RED == 1
    assert AirCrushColor.ORN == 2
    assert AirCrushColor.YEL == 3
    assert AirCrushColor.GRN == 4
    assert AirCrushColor.AQA == 5
    assert AirCrushColor.BLU == 6
    assert AirCrushColor.PPL == 7
    assert AirCrushColor.VLT == 8
    assert AirCrushColor.PPL_ALT == 9
    assert AirCrushColor.GRY == 10
    assert AirCrushColor.BLK == 11
    assert AirCrushColor.LIM == 12
    assert AirCrushColor.CYN == 13
    assert AirCrushColor.DGR == 14
    assert AirCrushColor.PNK == 15
    assert AirCrushColor.NON == 35
    assert Note.air_crush_begin(1, 2, 1, 80, 0, variation_id=AirCrushColor.NON).variation_id == 35


def test_air_color_values_match_umgr_color_enum():
    assert AirColor.PNK == 2
    assert AirColor.GRN == 3
    assert list(AirColor) == [AirColor.PNK, AirColor.GRN]


def test_note_factories_require_geometry_and_specific_fields():
    with pytest.raises(TypeError):
        Note.tap(tick=1, x=2)
    with pytest.raises(TypeError):
        Note.air_crush_begin(1, 2, 1)
    with pytest.raises(TypeError):
        Note.air_slide_begin(1, 2, 1)
    with pytest.raises(TypeError):
        Note.air_hold_begin(1, 2, 1)


def test_child_builds_long_note_chains():
    slide_begin = Note.slide_begin(10, 0, 4)
    slide_step = Note.slide_step(20, 6, 4)
    slide_end = Note.slide_end(30, 12, 4)

    slide = slide_begin.child(slide_step, slide_end)

    assert slide is slide_begin
    assert slide.children == [slide_step, slide_end]

    hold_begin = Note.hold_begin(40, 2, 4)
    hold_end = Note.hold_end(50, 2, 4)
    assert hold_begin.child(hold_end) is hold_begin
    assert hold_begin.children == [hold_end]

    air_slide_begin = Note.air_slide_begin(60, 4, 8, 80)
    air_slide_step = Note.air_slide_step(70, 8, 8, 120)
    air_slide_end = Note.air_slide_end(80, 12, 8, 80)
    assert air_slide_begin.child(air_slide_step, air_slide_end) is air_slide_begin
    assert air_slide_begin.children == [air_slide_step, air_slide_end]

    air_hold_begin = Note.air_hold_begin(90, 4, 8, 80)
    air_hold_end = Note.air_hold_end(100, 4, 8, 80)
    assert air_hold_begin.child(air_hold_end) is air_hold_begin
    assert air_hold_begin.children == [air_hold_end]

    air_crush_begin = Note.air_crush_begin(110, 4, 8, 80, 5)
    air_crush_control = Note.air_crush_control(120, 8, 8, 120, 0)
    air_crush_end = Note.air_crush_end(130, 12, 8, 80, 0)
    assert air_crush_begin.child(air_crush_control, air_crush_end) is air_crush_begin
    assert air_crush_begin.children == [air_crush_control, air_crush_end]


def test_child_with_no_arguments_clears_children():
    note = Note.tap(960, 4, 2, height=700)

    assert note.child() is note
    assert note.children == []


def test_child_adds_airlike_children_to_single_note():
    note = Note.tap(960, 4, 2)
    air = Note.air(960, 4, 2, direction=Direction.UP)
    air_slide = Note.air_slide_begin(960, 4, 2, 80).child(
        Note.air_slide_end(1440, 8, 2, 80),
    )

    assert note.child(air, air_slide) is note
    assert note.children == [air, air_slide]


def test_slide_segment_factories_match_long_attr():
    assert Note.slide_step(10, 3, 1).long_attr is LongAttr.STEP
    assert Note.slide_control(10, 3, 1).long_attr is LongAttr.CONTROL
    assert Note.slide_curve_control(10, 3, 1).long_attr is LongAttr.CURVE_CONTROL
    assert Note.slide_end(10, 3, 1).long_attr is LongAttr.END


def test_air_slide_segment_factories_match_long_attr():
    begin = Note.air_slide_begin(11, 4, 1, 80)
    assert begin.long_attr is LongAttr.BEGIN
    assert Note.air_slide_step(11, 4, 1, 80).long_attr is LongAttr.STEP
    assert Note.air_slide_control(11, 4, 1, 80).long_attr is LongAttr.CONTROL
    assert Note.air_slide_curve_control(11, 4, 1, 80).long_attr is LongAttr.CURVE_CONTROL
    assert Note.air_slide_end(11, 4, 1, 80).long_attr is LongAttr.END
    assert Note.air_slide_end_noact(11, 4, 1, 80).long_attr is LongAttr.END_NOACT


def test_air_hold_segment_factories_match_long_attr():
    assert Note.air_hold_begin(11, 4, 1, 80).long_attr is LongAttr.BEGIN
    assert Note.air_hold_step(11, 4, 1, 80).long_attr is LongAttr.STEP
    assert Note.air_hold_end(11, 4, 1, 80).long_attr is LongAttr.END
    assert Note.air_hold_end_noact(11, 4, 1, 80).long_attr is LongAttr.END_NOACT


def test_air_crush_segment_factories_match_long_attr():
    begin = Note.air_crush_begin(11, 4, 1, 80, 5)
    assert begin.long_attr is LongAttr.BEGIN
    assert begin.option_value == 5
    assert Note.air_crush_control(11, 4, 1, 80, 0).long_attr is LongAttr.CONTROL
    assert Note.air_crush_end(11, 4, 1, 80, 0).long_attr is LongAttr.END


def test_note_defaults_and_tap_constructor_are_pythonic():
    note = Note.tap(960, 4, 1)

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.NONE
    assert note.direction is Direction.NONE
    assert note.ex_attr is ExAttr.NONE
    assert note.tick == 960
    assert note.x == 4
    assert note.width == 1
    assert note.height == 800
    assert note.id is None
    assert note.children == []


def test_non_air_shape_factories_default_height_to_800():
    assert Note.extap(1, 2, 1).height == 800
    assert Note.flick(1, 2, 1).height == 800
    assert Note.damage(1, 2, 1).height == 800
    assert Note.hold_begin(1, 2, 1).height == 800
    assert Note.slide_begin(1, 2, 1).height == 800
    assert Note.air(1, 2, 1).height == 800


def test_note_dataclass_accepts_mp_noteinfo_order_as_positional_arguments():
    note = Note(
        NoteType.TAP,
        LongAttr.BEGIN,
        Direction.UP,
        ExAttr.HAS_NOTE,
        2,
        4,
        1,
        800,
        960,
        3,
        7,
        id=12,
    )

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.BEGIN
    assert note.direction is Direction.UP
    assert note.ex_attr is ExAttr.HAS_NOTE
    assert note.variation_id == 2
    assert note.tick == 960
    assert note.x == 4
    assert note.width == 1
    assert note.height == 800
    assert note.timeline_id == 3
    assert note.option_value == 7
    assert note.id == 12

    with pytest.raises(TypeError):
        Note(NoteType.TAP, LongAttr.NONE, Direction.NONE, ExAttr.NONE, 0, 4, 1, 800, 960, 0, 0, [])


def test_event_dataclasses_accept_required_fields_as_positional_arguments():
    assert BpmEvent(0, 120.0) == BpmEvent(tick=0, bpm=120.0)
    assert BeatChangeEvent(0, 4, 4) == BeatChangeEvent(
        bar=0,
        beats_per_bar=4,
        beat_unit=4,
    )
    assert TimelineSpeedEvent(2, 960, 0.75) == TimelineSpeedEvent(
        tick=960,
        timeline_id=2,
        speed=0.75,
    )
    assert NoteSpeedEvent(960, 1.25) == NoteSpeedEvent(tick=960, speed=1.25)


def test_note_bar_getter_represents_tick_as_reduced_beat_fraction():
    note = Note.tap(240, 4, 1)

    assert note.bar == (1, 8)

    note.tick = 480
    assert note.bar == (1, 4)

    note.tick = 1920
    assert note.bar == (1, 1)

    note.tick = 300
    assert note.bar == (5, 32)


def test_note_bar_setter_updates_tick_from_beat_fraction():
    note = Note.tap(0, 4, 1)

    note.bar = (1, 8)
    assert note.tick == 240
    assert note.bar == (1, 8)

    note.bar = (1, 4)
    assert note.tick == 480
    assert note.bar == (1, 4)


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
        children=[Note.tap(180, 5, 1)],
    )

    proto = note.to_proto()
    restored = Note.from_proto(proto)

    assert proto.id == 10
    assert proto.type == messages_pb2.NOTE_TYPE_SLIDE
    assert proto.long_attr == messages_pb2.LONG_ATTR_BEGIN
    assert restored == note


def test_chart_from_begin_edit_response_builds_event_snapshot():
    response = messages_pb2.BeginEditResponse(
        current_tick=240,
        notes=[messages_pb2.Note(type=messages_pb2.NOTE_TYPE_TAP, tick=240, x=1)],
        event_scan_until_tick=4800,
        event_scan_timeline_ids=[0, 2],
        bpm_events=[messages_pb2.BpmEvent(tick=0, bpm=120.0)],
        beat_change_events=[messages_pb2.BeatChangeEvent(bar=0, beats_per_bar=4, beat_unit=4)],
        timeline_speed_events=[
            messages_pb2.TimelineSpeedEvent(tick=960, timeline_id=2, speed=0.75)
        ],
        note_speed_events=[messages_pb2.NoteSpeedEvent(tick=960, speed=1.25)],
    )

    chart = Chart.from_begin_edit_response(response)
    chart.events.bpm[0].bpm = 180.0

    assert chart.notes == [Note(type=NoteType.TAP, tick=240, x=1)]
    assert chart.events.bpm == [BpmEvent(0, 180.0)]
    assert chart.events.beat == [BeatChangeEvent(0, 4, 4)]
    assert chart.events.til == [TimelineSpeedEvent(2, 960, 0.75)]
    assert chart.events.note_speed == [NoteSpeedEvent(960, 1.25)]


def test_event_normalization_uses_last_write_wins_by_key():
    chart = Chart(
        events=ChartEvents(
            bpm=[BpmEvent(0, 120.0), BpmEvent(0, 180.0)],
            beat=[
                BeatChangeEvent(bar=0, beats_per_bar=3, beat_unit=4),
                BeatChangeEvent(bar=0, beats_per_bar=4, beat_unit=4),
            ],
            til=[
                TimelineSpeedEvent(tick=960, timeline_id=1, speed=0.5),
                TimelineSpeedEvent(tick=960, timeline_id=1, speed=0.75),
            ],
            note_speed=[NoteSpeedEvent(480, 1.5), NoteSpeedEvent(480, 1.25)],
        ),
    )

    normalized = normalize_event_operations(chart)

    assert normalized.events.bpm == [BpmEvent(0, 180.0)]
    assert normalized.events.beat == [BeatChangeEvent(0, 4, 4)]
    assert normalized.events.til == [TimelineSpeedEvent(1, 960, 0.75)]
    assert normalized.events.note_speed == [NoteSpeedEvent(480, 1.25)]
