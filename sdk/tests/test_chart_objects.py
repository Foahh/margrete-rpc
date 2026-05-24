import pytest

from margrete_rpc import (
    AirCrush,
    AirCrushColor,
    AirCrushOption,
    AirDirection,
    BeatEvent,
    BpmEvent,
    Chart,
    ChartEvents,
    Damage,
    ExAttr,
    Extap,
    ExtapDirection,
    Flick,
    FlickDirection,
    Hold,
    L,
    LLNote,
    LongAttr,
    NoteInfo,
    NoteSpeedEvent,
    NoteType,
    Slide,
    Tap,
    TimelineSpeedEvent,
    UnsupportedNoteTree,
)
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.model import normalize_event_operations
from margrete_rpc.model.note import wrap_ll_note
from margrete_rpc.model.note.time import TICKS_PER_BEAT, Tick, beats_to_ticks


def test_note_type_factories_set_kind_and_geometry():
    assert L.tap(1, 2, 1).type is NoteType.TAP
    assert L.extap(1, 2, 1).type is NoteType.EXTAP
    assert L.flick(1, 2, 1).type is NoteType.FLICK
    assert L.damage(1, 2, 1).type is NoteType.DAMAGE
    assert L.hold_begin(1, 2, 1).type is NoteType.HOLD
    assert L.hold_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert L.hold_end(1, 2, 1).long_attr is LongAttr.END
    assert L.slide_begin(1, 2, 1).type is NoteType.SLIDE
    assert L.slide_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert L.air(1, 2, 1).type is NoteType.AIR
    assert L.air_slide_begin(1, 2, 1, 80).type is NoteType.AIRSLIDE
    assert L.air_hold_begin(1, 2, 1, 80).type is NoteType.AIRHOLD
    assert L.air_hold_begin(1, 2, 1, 80).long_attr is LongAttr.BEGIN
    assert L.air_hold_end(1, 2, 1, 80).long_attr is LongAttr.END
    crush0 = L.air_crush_begin(1, 2, 1, 80, AirCrushOption.TRACELIKE)
    assert crush0.type is NoteType.AIRCRUSH
    assert crush0.long_attr is LongAttr.BEGIN
    assert crush0.option_value == AirCrushOption.TRACELIKE
    head = L.air_crush_begin(1, 2, 1, 80, AirCrushOption.HEAD_ONLY)
    assert head.option_value == 0x7FFFFFFF
    assert L.air_crush_begin(1, 2, 1, 80, 120).option_value == 120


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
    assert L.air_crush_begin(1, 2, 1, 80, 0, variation_id=AirCrushColor.NON).variation_id == 35


def test_note_enums_remain_public_exports():
    from margrete_rpc import (
        AirCrushColor,
        AirCrushOption,
        AirDirection,
        ExAttr,
        ExtapDirection,
        FlickDirection,
        LongAttr,
        NoteType,
    )

    assert NoteType.TAP.value == messages_pb2.NOTE_TYPE_TAP
    assert LongAttr.END_NOACT.value == messages_pb2.LONG_ATTR_END_NOACT
    assert ExtapDirection.NONE.value == messages_pb2.DIRECTION_NONE
    assert ExtapDirection.UP.value == messages_pb2.DIRECTION_UP
    assert AirDirection.DOWNRIGHT.value == messages_pb2.DIRECTION_DOWNRIGHT
    assert ExtapDirection.OUTIN.value == messages_pb2.DIRECTION_OUTIN
    assert FlickDirection.RIGHT.value == messages_pb2.DIRECTION_RIGHT
    assert ExAttr.INVERT.value == messages_pb2.EX_ATTR_INVERT
    assert AirCrushOption.HEAD_ONLY == 0x7FFFFFFF
    assert AirCrushColor.NON == 35


def test_new_note_api_is_exported_from_root_package():
    from margrete_rpc import (
        AirCrush,
        HLNote,
        Hold,
        L,
        LLNote,
        NoteInfo,
        Slide,
        Tap,
        UnsupportedNoteTree,
    )

    assert L.tap(0, 4, 2).type is NoteType.TAP
    assert LLNote().info == NoteInfo()
    assert isinstance(Tap(0, 4, 2), HLNote)
    assert Hold is not None
    assert Slide is not None
    assert AirCrush is not None
    assert issubclass(UnsupportedNoteTree, ValueError)


def test_note_factories_require_geometry_and_specific_fields():
    with pytest.raises(TypeError):
        L.tap(tick=1, x=2)
    with pytest.raises(TypeError):
        L.air_crush_begin(1, 2, 1)
    with pytest.raises(TypeError):
        L.air_slide_begin(1, 2, 1)
    with pytest.raises(TypeError):
        L.air_hold_begin(1, 2, 1)


def test_child_builds_long_note_chains():
    slide_begin = L.slide_begin(10, 0, 4)
    slide_step = L.slide_step(20, 6, 4)
    slide_end = L.slide_end(30, 12, 4)

    slide = slide_begin.child(slide_step, slide_end)

    assert slide is slide_begin
    assert slide.children == [slide_step, slide_end]

    hold_begin = L.hold_begin(40, 2, 4)
    hold_end = L.hold_end(50, 2, 4)
    assert hold_begin.child(hold_end) is hold_begin
    assert hold_begin.children == [hold_end]

    air_slide_begin = L.air_slide_begin(60, 4, 8, 80)
    air_slide_step = L.air_slide_step(70, 8, 8, 120)
    air_slide_end = L.air_slide_end(80, 12, 8, 80)
    assert air_slide_begin.child(air_slide_step, air_slide_end) is air_slide_begin
    assert air_slide_begin.children == [air_slide_step, air_slide_end]

    air_hold_begin = L.air_hold_begin(90, 4, 8, 80)
    air_hold_end = L.air_hold_end(100, 4, 8, 80)
    assert air_hold_begin.child(air_hold_end) is air_hold_begin
    assert air_hold_begin.children == [air_hold_end]

    air_crush_begin = L.air_crush_begin(110, 4, 8, 80, 5)
    air_crush_control = L.air_crush_control(120, 8, 8, 120, 0)
    air_crush_end = L.air_crush_end(130, 12, 8, 80, 0)
    assert air_crush_begin.child(air_crush_control, air_crush_end) is air_crush_begin
    assert air_crush_begin.children == [air_crush_control, air_crush_end]


def test_child_with_no_arguments_clears_children():
    note = L.tap(960, 4, 2, height=700)

    assert note.child() is note
    assert note.children == []


def test_child_adds_airlike_children_to_single_note():
    note = L.tap(960, 4, 2)
    air = L.air(960, 4, 2, direction=AirDirection.UP)
    air_slide = L.air_slide_begin(960, 4, 2, 80).child(
        L.air_slide_end(1440, 8, 2, 80),
    )

    assert note.child(air, air_slide) is note
    assert note.children == [air, air_slide]


def test_slide_segment_factories_match_long_attr():
    assert L.slide_step(10, 3, 1).long_attr is LongAttr.STEP
    assert L.slide_control(10, 3, 1).long_attr is LongAttr.CONTROL
    assert L.slide_curve_control(10, 3, 1).long_attr is LongAttr.CURVE_CONTROL
    assert L.slide_end(10, 3, 1).long_attr is LongAttr.END


def test_air_slide_segment_factories_match_long_attr():
    begin = L.air_slide_begin(11, 4, 1, 80)
    assert begin.long_attr is LongAttr.BEGIN
    assert L.air_slide_step(11, 4, 1, 80).long_attr is LongAttr.STEP
    assert L.air_slide_control(11, 4, 1, 80).long_attr is LongAttr.CONTROL
    assert L.air_slide_curve_control(11, 4, 1, 80).long_attr is LongAttr.CURVE_CONTROL
    assert L.air_slide_end(11, 4, 1, 80).long_attr is LongAttr.END
    assert L.air_slide_end_noact(11, 4, 1, 80).long_attr is LongAttr.END_NOACT


def test_air_hold_segment_factories_match_long_attr():
    assert L.air_hold_begin(11, 4, 1, 80).long_attr is LongAttr.BEGIN
    assert L.air_hold_step(11, 4, 1, 80).long_attr is LongAttr.STEP
    assert L.air_hold_end(11, 4, 1, 80).long_attr is LongAttr.END
    assert L.air_hold_end_noact(11, 4, 1, 80).long_attr is LongAttr.END_NOACT


def test_air_crush_segment_factories_match_long_attr():
    begin = L.air_crush_begin(11, 4, 1, 80, 5)
    assert begin.long_attr is LongAttr.BEGIN
    assert begin.option_value == 5
    assert L.air_crush_control(11, 4, 1, 80, 0).long_attr is LongAttr.CONTROL
    assert L.air_crush_end(11, 4, 1, 80, 0).long_attr is LongAttr.END


def test_note_defaults_and_tap_constructor_are_pythonic():
    note = L.tap(960, 4, 1)

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.NONE
    assert note.direction == messages_pb2.DIRECTION_UP
    assert note.ex_attr is ExAttr.NONE
    assert note.tick == 960
    assert note.x == 4
    assert note.width == 1
    assert note.height == 800
    assert note.id is None
    assert note.children == []


def test_non_air_shape_factories_default_height_to_800():
    assert L.extap(1, 2, 1).height == 800
    assert L.flick(1, 2, 1).height == 800
    assert L.damage(1, 2, 1).height == 800
    assert L.hold_begin(1, 2, 1).height == 800
    assert L.slide_begin(1, 2, 1).height == 800
    assert L.air(1, 2, 1).height == 800


def test_noteinfo_dataclass_accepts_mp_noteinfo_order_as_positional_arguments():
    info = NoteInfo(
        NoteType.TAP,
        LongAttr.BEGIN,
        ExtapDirection.UP,
        ExAttr.HAS_NOTE,
        2,
        4,
        1,
        800,
        960,
        3,
        7,
    )
    note = LLNote(info=info, id=12)

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.BEGIN
    assert note.direction == ExtapDirection.UP
    assert note.ex_attr is ExAttr.HAS_NOTE
    assert note.variation_id == 2
    assert note.tick == 960
    assert note.x == 4
    assert note.width == 1
    assert note.height == 800
    assert note.timeline_id == 3
    assert note.option_value == 7
    assert note.id == 12


def test_event_dataclasses_accept_required_fields_as_positional_arguments():
    assert BpmEvent(0, 120.0) == BpmEvent(tick=0, bpm=120.0)
    assert BeatEvent(0, 4, 4) == BeatEvent(
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


def test_ll_note_tick_uses_int_and_beats_to_ticks_for_fractions():
    note = L.tap(0, 4, 1)
    assert note.tick == 0
    note.tick = note.tick + beats_to_ticks((1, 8))
    assert note.tick == 240
    note.tick = note.tick + beats_to_ticks((1, 8))
    assert note.tick == 480
    note.tick = note.tick - beats_to_ticks((1, 4))
    assert note.tick == 0


def test_ll_note_tick_augmented_assignment_matches_direct_tick_math():
    note = L.tap(240, 4, 1)
    note.tick = 480
    assert note.tick == 480
    note.tick = 1920
    assert note.tick == 1920
    note.tick = 300
    assert note.tick == 300


def test_tick_assignment_accepts_beat_fraction_tuple_on_hl_only():
    note = L.tap(0, 4, 1)
    note.tick = beats_to_ticks((1, 8))
    assert note.tick == 240
    tap = Tap(tick=960, x=4, width=2)
    tap.tick = (1, 4)
    assert tap.tick == 480


def test_beats_to_ticks_rejects_non_whole_tick():
    with pytest.raises(ValueError, match="whole tick"):
        beats_to_ticks((1, 7))


def test_beats_to_ticks_rejects_denominator_above_ticks_per_beat():
    with pytest.raises(ValueError, match="denominator must not exceed"):
        beats_to_ticks((1, TICKS_PER_BEAT + 1))


def test_beats_to_ticks_rejects_non_int_types():
    with pytest.raises(TypeError):
        beats_to_ticks((1, 2.0))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        beats_to_ticks("bad")  # type: ignore[arg-type]


def test_tick_wraps_same_storage_for_ll_and_hl():
    note = L.tap(0, 4, 1)
    assert type(note.tick) is int
    note.tick = note.tick + beats_to_ticks((1, 8))
    assert note.info.tick == 240

    tap = Tap(tick=0, x=4, width=2)
    assert isinstance(tap.tick, Tick)
    tap.tick += (1, 4)
    assert int(tap.tick) == 480


def test_note_round_trips_to_protobuf_with_children_and_id():
    note = LLNote(
        id=10,
        info=NoteInfo(
            type=NoteType.SLIDE,
            long_attr=LongAttr.BEGIN,
            direction=AirDirection.UPLEFT,
            ex_attr=ExAttr.HAS_NOTE,
            variation_id=2,
            x=3,
            width=2,
            height=1,
            tick=120,
            timeline_id=4,
            option_value=9,
        ),
        children=[L.tap(180, 5, 1)],
    )

    proto = note.to_proto()
    restored = LLNote.from_proto(proto)

    assert proto.id == 10
    assert proto.type == messages_pb2.NOTE_TYPE_SLIDE
    assert proto.long_attr == messages_pb2.LONG_ATTR_BEGIN
    assert restored == note


def test_llnote_info_properties_delegate_to_info():
    note = LLNote()

    note.type = NoteType.TAP
    note.long_attr = LongAttr.BEGIN
    note.direction = ExtapDirection.UP
    note.ex_attr = ExAttr.HAS_NOTE
    note.variation_id = 2
    note.x = 4
    note.width = 1
    note.height = 800
    note.tick = 960
    note.timeline_id = 3
    note.option_value = 7

    assert note.info == NoteInfo(
        type=NoteType.TAP,
        long_attr=LongAttr.BEGIN,
        direction=ExtapDirection.UP,
        ex_attr=ExAttr.HAS_NOTE,
        variation_id=2,
        x=4,
        width=1,
        height=800,
        tick=960,
        timeline_id=3,
        option_value=7,
    )


def test_l_factory_methods_build_low_level_notes():
    assert L.tap(1, 2, 1).type is NoteType.TAP
    assert L.extap(1, 2, 1).type is NoteType.EXTAP
    assert L.flick(1, 2, 1).type is NoteType.FLICK
    assert L.damage(1, 2, 1).type is NoteType.DAMAGE
    assert L.hold_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert L.hold_end(2, 2, 1).long_attr is LongAttr.END
    assert L.slide_begin(1, 2, 1).type is NoteType.SLIDE
    assert L.air(1, 2, 1, direction=AirDirection.UP).direction == AirDirection.UP
    assert L.air_slide_end_noact(2, 4, 1, 80).long_attr is LongAttr.END_NOACT
    assert L.air_hold_end_noact(2, 4, 1, 80).long_attr is LongAttr.END_NOACT
    assert L.air_crush_begin(1, 2, 1, 80, AirCrushOption.HEAD_ONLY).option_value == 0x7FFFFFFF


def test_llnote_round_trips_to_protobuf_with_children_and_id():
    note = LLNote(
        id=10,
        info=NoteInfo(
            type=NoteType.SLIDE,
            long_attr=LongAttr.BEGIN,
            direction=AirDirection.UPLEFT,
            ex_attr=ExAttr.HAS_NOTE,
            variation_id=2,
            x=3,
            width=2,
            height=1,
            tick=120,
            timeline_id=4,
            option_value=9,
        ),
        children=[L.tap(180, 5, 1)],
    )

    proto = note.to_proto()
    restored = LLNote.from_proto(proto)

    assert proto.id == 10
    assert proto.type == messages_pb2.NOTE_TYPE_SLIDE
    assert proto.long_attr == messages_pb2.LONG_ATTR_BEGIN
    assert restored == note


def test_tap_redirects_shared_ll_fields_and_converts_to_ll():
    tap = Tap(tick=960, x=4, width=2)
    tap.x = 5
    tap.height = 700
    tap.til = 3
    tap._info.ex_attr = ExAttr.HAS_NOTE
    tap.tick = 480

    ll = tap.to_ll()

    assert tap.tick == 480
    assert tap.x == 5
    assert tap.width == 2
    assert tap.height == 700
    assert tap.til == 3
    assert tap._info.ex_attr is ExAttr.HAS_NOTE
    assert ll.type is NoteType.TAP
    assert ll.long_attr is LongAttr.NONE
    assert ll.tick == 480
    assert ll.x == 5
    assert ll.width == 2
    assert ll.height == 700
    assert ll.timeline_id == 3
    assert ll.ex_attr is ExAttr.HAS_NOTE
    assert ll.children == []


def test_high_level_to_ll_copies_note_info_instead_of_aliasing():
    tap = Tap(tick=960, x=4, width=2)

    ll = tap.to_ll()
    ll.tick = 480
    ll.x = 8

    assert tap.tick == 960
    assert tap.x == 4


def test_high_level_ground_note_geometry_is_backed_by_note_info():
    extap = Extap(tick=960, x=4, width=2, direction=ExtapDirection.UP)

    assert extap._info.tick == 960
    assert extap._info.x == 4
    assert extap._info.width == 2
    assert extap._info.direction == ExtapDirection.UP

    extap.tick = 480
    extap.x = 5
    extap.width = 3
    extap.direction = ExtapDirection.DOWN

    assert extap._info.tick == 480
    assert extap._info.x == 5
    assert extap._info.width == 3
    assert extap._info.direction == ExtapDirection.DOWN

    extap._info.tick = 240
    extap._info.x = 6
    extap._info.width = 4
    extap._info.direction = ExtapDirection.CENTER

    assert extap.tick == 240
    assert extap.x == 6
    assert extap.width == 4
    assert extap.direction is ExtapDirection.CENTER


def test_tap_air_adds_single_air_child():
    tap = Tap(tick=0, x=4, width=2)

    air = tap.air(AirDirection.DOWN)
    ll = tap.to_ll()

    assert air.direction is AirDirection.DOWN
    assert len(ll.children) == 1
    assert ll.children[0].type is NoteType.AIR
    assert ll.children[0].direction == AirDirection.DOWN


def test_ground_note_rejects_multiple_air_objects():
    tap = Tap(tick=0, x=4, width=2)
    tap.air(AirDirection.UP)

    with pytest.raises(ValueError, match="only one air"):
        tap.air(AirDirection.DOWN)


def test_high_level_short_notes_validate_tick_and_width():
    with pytest.raises(ValueError, match="tick must be non-negative"):
        Tap(tick=-1, x=4, width=2)

    with pytest.raises(ValueError, match="width must be at least 1"):
        Tap(tick=0, x=4, width=0)


def test_ground_note_direction_is_available_only_on_extap_and_flick():
    tap = Tap(tick=0, x=4, width=2)
    damage = Damage(tick=0, x=4, width=2)

    assert not hasattr(tap, "direction")
    assert not hasattr(damage, "direction")
    assert Extap(tick=0, x=4, width=2).direction is ExtapDirection.UP
    assert Flick(tick=0, x=4, width=2).direction is FlickDirection.AUTO


@pytest.mark.parametrize(
    "direction",
    [
        ExtapDirection.NONE,
        ExtapDirection.UP,
        ExtapDirection.DOWN,
        ExtapDirection.CENTER,
        ExtapDirection.LEFT,
        ExtapDirection.RIGHT,
        ExtapDirection.ROTATE_LEFT,
        ExtapDirection.ROTATE_RIGHT,
        ExtapDirection.INOUT,
        ExtapDirection.OUTIN,
    ],
)
def test_extap_accepts_only_extap_directions(direction):
    extap = Extap(tick=0, x=4, width=2, direction=direction)

    assert extap.direction is direction

    extap.direction = direction
    assert extap._info.direction == direction


@pytest.mark.parametrize(
    "direction",
    [
        messages_pb2.DIRECTION_AUTO,
        messages_pb2.DIRECTION_UPLEFT,
    ],
)
def test_extap_rejects_invalid_directions(direction):
    with pytest.raises(ValueError, match="invalid extap direction"):
        Extap(tick=0, x=4, width=2, direction=direction)

    extap = Extap(tick=0, x=4, width=2)
    with pytest.raises(ValueError, match="invalid extap direction"):
        extap.direction = direction


@pytest.mark.parametrize(
    "direction", [FlickDirection.AUTO, FlickDirection.LEFT, FlickDirection.RIGHT]
)
def test_flick_accepts_only_flick_directions(direction):
    flick = Flick(tick=0, x=4, width=2, direction=direction)

    assert flick.direction is direction

    flick.direction = direction
    assert flick._info.direction == direction


@pytest.mark.parametrize(
    "direction",
    [
        messages_pb2.DIRECTION_NONE,
        messages_pb2.DIRECTION_UP,
        messages_pb2.DIRECTION_DOWN,
    ],
)
def test_flick_rejects_invalid_directions(direction):
    with pytest.raises(ValueError, match="invalid flick direction"):
        Flick(tick=0, x=4, width=2, direction=direction)

    flick = Flick(tick=0, x=4, width=2)
    with pytest.raises(ValueError, match="invalid flick direction"):
        flick.direction = direction


@pytest.mark.parametrize(
    "direction",
    [
        AirDirection.UP,
        AirDirection.DOWN,
        AirDirection.UPLEFT,
        AirDirection.UPRIGHT,
        AirDirection.DOWNLEFT,
        AirDirection.DOWNRIGHT,
    ],
)
def test_air_accepts_only_air_directions(direction):
    air = Tap(tick=0, x=4, width=2).air(direction)

    assert air.direction is direction

    air.direction = direction
    assert air._info.direction == direction


@pytest.mark.parametrize(
    "direction",
    [
        messages_pb2.DIRECTION_NONE,
        messages_pb2.DIRECTION_AUTO,
        messages_pb2.DIRECTION_LEFT,
        messages_pb2.DIRECTION_RIGHT,
    ],
)
def test_air_rejects_invalid_directions(direction):
    tap = Tap(tick=0, x=4, width=2)

    with pytest.raises(ValueError, match="invalid air direction"):
        tap.air(direction)

    air = tap.air(AirDirection.UP)
    with pytest.raises(ValueError, match="invalid air direction"):
        air.direction = direction


def test_slide_requires_end_and_converts_ordered_joints():
    slide = Slide(tick=960, x=0, width=4).step(1440, x=6, width=4).control(1680, x=8, width=4)

    with pytest.raises(ValueError, match="requires an end joint"):
        slide.to_ll()

    partial = slide.to_ll(skip_validation=True)
    assert partial.type is NoteType.SLIDE
    assert [c.long_attr for c in partial.children] == [
        LongAttr.STEP,
        LongAttr.CONTROL,
    ]

    ll = slide.end(1920, x=12, width=4).to_ll()

    assert ll.type is NoteType.SLIDE
    assert ll.long_attr is LongAttr.BEGIN
    assert [child.long_attr for child in ll.children] == [
        LongAttr.STEP,
        LongAttr.CONTROL,
        LongAttr.END,
    ]


def test_debug_str_matches_repr_and_includes_tick_and_enum_name_value():
    tap = Tap(tick=1920, x=1, width=2)
    assert str(tap) == repr(tap)
    assert "Tap(" in str(tap)
    assert "tick=1920" in str(tap)
    ll = L.tap(1920, 1, 2)
    assert str(ll) == repr(ll)
    assert "tick=1920" in str(ll)
    assert "NoteType.TAP(" in str(ll) and ")" in str(ll)


def test_high_level_str_prints_attached_air_as_children():
    tap = Tap(tick=0, x=4, width=2)
    tap.air(AirDirection.DOWN).slide(height=80).end(960, x=8, width=2, height=100)

    lines = str(tap).splitlines()

    assert lines[0].startswith("Tap(")
    assert lines[1].startswith("  Air(")
    assert lines[2].startswith("    AirSlide(")
    assert "air=" not in lines[0]
    assert "long_action=" not in lines[1]


def test_slide_rejects_joints_after_end_and_non_increasing_ticks():
    slide = Slide(tick=960, x=0, width=4)

    with pytest.raises(ValueError, match="must be later"):
        slide.step(960, x=6, width=4)

    slide.step(1440, x=6, width=4).end(1920, x=12, width=4)

    with pytest.raises(ValueError, match="already ended"):
        slide.control(2160, x=8, width=4)


def test_hold_requires_end_and_defaults_end_geometry_to_begin():
    hold = Hold(tick=0, x=4, width=2)

    with pytest.raises(ValueError, match="requires an end joint"):
        hold.to_ll()

    ll = hold.end(960).to_ll()

    assert ll.type is NoteType.HOLD
    assert len(ll.children) == 1
    assert ll.children[0].long_attr is LongAttr.END
    assert ll.children[0].x == 4
    assert ll.children[0].width == 2


def test_air_slide_forces_upward_air_and_supports_end_noact():
    tap = Tap(tick=0, x=4, width=2)
    air_slide = tap.air(AirDirection.DOWN).slide(height=80)

    with pytest.raises(ValueError, match="requires an end joint"):
        tap.to_ll()

    air_slide.control(480, x=6, width=2, height=120).end_noact(960, x=8, width=2, height=80)
    ll = tap.to_ll()

    air = ll.children[0]
    air_long = air.children[0]
    assert air.direction is AirDirection.UP
    assert air_long.type is NoteType.AIRSLIDE
    assert air_long.children[-1].long_attr is LongAttr.END_NOACT


def test_air_invert_maps_to_ex_attr_invert_on_ll():
    tap = Tap(tick=0, x=4, width=2)
    air = tap.air(AirDirection.DOWN)
    air.inverted = True
    air.til = 3
    air.tick += (1, 4)

    ll = tap.to_ll().children[0]

    assert air.inverted is True
    assert air.tick == 480
    assert ll.ex_attr is ExAttr.INVERT
    assert ll.timeline_id == 3
    assert ll.tick == 480


def test_air_geometry_and_direction_are_backed_by_note_info():
    air = Tap(tick=0, x=4, width=2).air(AirDirection.DOWN)

    assert air._info.tick == 0
    assert air._info.x == 4
    assert air._info.width == 2
    assert air._info.direction == AirDirection.DOWN

    air.tick = 480
    air.x = 5
    air.width = 3
    air.direction = AirDirection.UP

    assert air._info.tick == 480
    assert air._info.x == 5
    assert air._info.width == 3
    assert air._info.direction == AirDirection.UP

    air._info.tick = 240
    air._info.x = 6
    air._info.width = 4
    air._info.direction = AirDirection.DOWNLEFT

    assert air.tick == 240
    assert air.x == 6
    assert air.width == 4
    assert air.direction is AirDirection.DOWNLEFT


def test_air_slide_and_air_hold_do_not_expose_color_on_hl_builder():
    tap = Tap(tick=0, x=4, width=2)
    air_slide = tap.air(AirDirection.DOWN).slide(height=80)
    air_slide.end(960, x=8, width=2, height=100)

    hold = Tap(tick=1200, x=4, width=2).air(AirDirection.UP).hold(height=120)
    hold.end_noact(1680, x=4, width=2, height=140)

    assert tap.to_ll().children[0].children[0].variation_id == 0
    assert hold.to_ll().variation_id == 0


def test_air_crush_allows_controls_only_and_requires_end():
    crush = AirCrush(tick=0, x=4, width=2, height=80, density=5)

    with pytest.raises(ValueError, match="requires an end joint"):
        crush.to_ll()

    ll = crush.control(480, x=6, width=2, height=120).end(960, x=8, width=2, height=80).to_ll()

    assert ll.type is NoteType.AIRCRUSH
    assert [child.long_attr for child in ll.children] == [LongAttr.CONTROL, LongAttr.END]


def test_air_crush_density_and_color_redirect_to_ll_storage_fields():
    crush = AirCrush(
        tick=0,
        x=4,
        width=2,
        height=80,
        density=AirCrushOption.TRACELIKE,
        color=AirCrushColor.RED,
    )
    crush.density = 120
    crush.color = AirCrushColor.NON
    crush.til = 2
    ll = crush.end(960, x=8, width=2, height=100).to_ll()

    assert crush.density == 120
    assert crush.color is AirCrushColor.NON
    assert ll.option_value == 120
    assert ll.variation_id == AirCrushColor.NON
    assert ll.timeline_id == 2
    assert ll.children[0].option_value == 0


def test_air_crush_density_accepts_beat_tuple_and_iadd():
    crush = AirCrush(tick=0, x=4, width=2, height=80, density=0)
    crush.density = (1, 8)
    assert crush.density == 240
    assert isinstance(crush.density, Tick)
    crush.density += (1, 8)
    assert crush.density == 480


def test_air_crush_density_rejects_iadd_when_head_only():
    crush = AirCrush(
        tick=0, x=4, width=2, height=80, density=AirCrushOption.HEAD_ONLY, color=AirCrushColor.DEF
    )
    with pytest.raises(ValueError, match="HEAD_ONLY"):
        crush.density += (1, 8)


def test_wrap_ll_note_supports_air_hold_with_steps_attached_to_air():
    ll = L.tap(19200, 4, 8).child(
        L.air(19200, 4, 8, direction=AirDirection.UP).child(
            L.air_hold_begin(19200, 4, 8, 80).child(
                L.air_hold_step(19680, 4, 8, 800),
                L.air_hold_end(20160, 4, 8, 800),
            )
        )
    )

    wrapped = wrap_ll_note(ll)
    restored = wrapped.to_ll()

    assert restored == ll


def test_long_note_begin_geometry_is_backed_by_note_info():
    slide = Slide(tick=960, x=0, width=4, height=800)

    assert slide._info.tick == 960
    assert slide._info.x == 0
    assert slide._info.width == 4
    assert slide._info.height == 800

    slide.tick = 480
    slide.x = 2
    slide.width = 3
    slide.height = 700

    assert slide._info.tick == 480
    assert slide._info.x == 2
    assert slide._info.width == 3
    assert slide._info.height == 700

    slide._info.tick = 240
    slide._info.x = 1
    slide._info.width = 2
    slide._info.height = 600

    assert slide.tick == 240
    assert slide.x == 1
    assert slide.width == 2
    assert slide.height == 600


def test_long_note_joint_geometry_is_backed_by_note_info():
    slide = Slide(tick=960, x=0, width=4).step(1440, x=6, width=3)
    joint = slide.joints[0]

    assert joint.info.tick == 1440
    assert joint.info.x == 6
    assert joint.info.width == 3
    assert joint.info.height == 800
    assert joint.info.long_attr is LongAttr.STEP

    joint.tick = 1680
    joint.x = 7
    joint.width = 2
    joint.height = 700
    joint.long_attr = LongAttr.CONTROL
    joint.info.option_value = 9

    assert joint.info.tick == 1680
    assert joint.info.x == 7
    assert joint.info.width == 2
    assert joint.info.height == 700
    assert joint.info.long_attr is LongAttr.CONTROL
    assert joint.info.option_value == 9

    joint.info.tick = 1920
    joint.info.x = 8
    joint.info.width = 1
    joint.info.height = 600
    joint.info.long_attr = LongAttr.END
    joint.info.option_value = 5

    assert joint.tick == 1920
    assert joint.x == 8
    assert joint.width == 1
    assert joint.height == 600
    assert joint.long_attr is LongAttr.END
    assert joint.info.option_value == 5


def test_long_note_exposes_joints_for_iteration():
    slide = (
        Slide(tick=960, x=0, width=4)
        .step(1440, x=6, width=3)
        .end(1920, x=12, width=4)
    )

    assert slide.joints is slide._joints
    assert [joint.long_attr for joint in slide.joints] == [
        LongAttr.STEP,
        LongAttr.END,
    ]
    assert slide.joints[-1].tick == 1920


def test_wrapped_long_note_joint_info_redirects_and_preserves_metadata():
    ll = L.slide_begin(960, 0, 4).child(
        L.slide_step(1440, 6, 3, timeline_id=2, ex_attr=ExAttr.HAS_NOTE),
        L.slide_end(1920, 12, 4),
    )

    wrapped = wrap_ll_note(ll)
    joint = wrapped.joints[0]
    joint.tick = 1680
    restored = wrapped.to_ll()

    assert isinstance(wrapped, Slide)
    assert joint.info.tick == 1680
    assert restored.children[0].tick == 1680
    assert restored.children[0].timeline_id == 2
    assert restored.children[0].ex_attr is ExAttr.HAS_NOTE


def test_wrap_ll_note_wraps_tap_and_preserves_noop_info():
    ll = L.tap(240, 1, 2, height=123, timeline_id=4)

    wrapped = wrap_ll_note(ll)
    wrapped.x = 5
    restored = wrapped.to_ll()

    assert isinstance(wrapped, Tap)
    assert restored.x == 5
    assert restored.height == 123
    assert restored.timeline_id == 4


def test_wrap_ll_note_wraps_slide_with_ordered_joints():
    ll = L.slide_begin(960, 0, 4, timeline_id=2).child(
        L.slide_step(1440, 6, 4),
        L.slide_control(1680, 8, 4),
        L.slide_end(1920, 12, 4),
    )

    wrapped = wrap_ll_note(ll)
    restored = wrapped.to_ll()

    assert isinstance(wrapped, Slide)
    assert restored == ll


def test_wrap_ll_note_rejects_invalid_begin_end_placement():
    invalid = L.slide_begin(960, 0, 4).child(
        L.slide_step(1440, 6, 4),
        L.slide_control(1200, 8, 4),
        L.slide_end(1920, 12, 4),
    )

    with pytest.raises(UnsupportedNoteTree):
        wrap_ll_note(invalid)


def test_wrap_ll_note_rejects_many_air_children():
    invalid = L.tap(0, 4, 2).child(
        L.air(0, 4, 2, direction=AirDirection.UP),
        L.air(0, 4, 2, direction=AirDirection.DOWN),
    )

    with pytest.raises(UnsupportedNoteTree):
        wrap_ll_note(invalid)


def test_wrap_ll_note_wraps_extap_with_none_direction():
    ll = L.extap(0, 4, 2, direction=messages_pb2.DIRECTION_NONE)

    wrapped = wrap_ll_note(ll)

    assert isinstance(wrapped, Extap)
    assert wrapped.direction is ExtapDirection.NONE


def test_chart_from_begin_edit_response_splits_wrapped_and_raw_notes():
    response = messages_pb2.BeginEditResponse(
        current_tick=240,
        notes=[
            messages_pb2.Note(id=1, type=messages_pb2.NOTE_TYPE_TAP, tick=240, x=1, width=2),
            messages_pb2.Note(
                id=2,
                type=messages_pb2.NOTE_TYPE_SLIDE,
                long_attr=messages_pb2.LONG_ATTR_BEGIN,
                tick=960,
                x=0,
                width=4,
                children=[
                    messages_pb2.Note(
                        type=messages_pb2.NOTE_TYPE_TAP,
                        long_attr=messages_pb2.LONG_ATTR_NONE,
                        tick=1440,
                        x=6,
                        width=4,
                    )
                ],
            ),
        ],
        event_scan_extra_tick=19200,
        event_scan_til=[0, 2],
        bpm_events=[messages_pb2.BpmEvent(tick=0, bpm=120.0)],
    )

    chart = Chart.from_begin_edit_response(response)

    assert len(chart.notes) == 1
    assert isinstance(chart.notes[0], Tap)
    assert len(chart.raw_notes) == 1
    assert chart.raw_notes[0].id == 2
    assert chart.events.bpm == [BpmEvent(0, 120.0)]


def test_chart_from_begin_edit_response_wraps_extap_with_none_direction():
    response = messages_pb2.BeginEditResponse(
        current_tick=240,
        notes=[
            messages_pb2.Note(
                id=1,
                type=messages_pb2.NOTE_TYPE_EXTAP,
                direction=messages_pb2.DIRECTION_NONE,
                tick=240,
                x=1,
                width=2,
            ),
        ],
    )

    chart = Chart.from_begin_edit_response(response)

    assert len(chart.notes) == 1
    assert chart.raw_notes == []
    assert isinstance(chart.notes[0], Extap)
    assert chart.notes[0].direction is ExtapDirection.NONE


def test_event_normalization_uses_last_write_wins_by_key():
    chart = Chart(
        events=ChartEvents(
            bpm=[BpmEvent(0, 120.0), BpmEvent(0, 180.0)],
            beat=[
                BeatEvent(bar=0, beats_per_bar=3, beat_unit=4),
                BeatEvent(bar=0, beats_per_bar=4, beat_unit=4),
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
    assert normalized.events.beat == [BeatEvent(0, 4, 4)]
    assert normalized.events.til == [TimelineSpeedEvent(1, 960, 0.75)]
    assert normalized.events.note_speed == [NoteSpeedEvent(480, 1.25)]
