import pytest

from margrete_rpc import (
    Air,
    AirCrush,
    AirDirection,
    AirHold,
    AirJoint,
    AirSlide,
    BeatEvent,
    BpmEvent,
    Chart,
    ChartEvents,
    Color,
    ColorValue,
    Damage,
    Direction,
    ExAttr,
    Extap,
    ExtapDirection,
    Flick,
    FlickDirection,
    Hold,
    Joint,
    JointKind,
    LongAttr,
    N,
    Node,
    Note,
    NoteInfo,
    NoteSpeedEvent,
    NoteType,
    Slide,
    Tap,
    TimelineSpeedEvent,
    UnsupportedNoteTree,
)
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import normalize_event_operations
from margrete_rpc.chart.note import wrap_node
from margrete_rpc.chart.time import TICKS_PER_BEAT, d2t


def test_note_type_factories_set_kind_and_geometry():
    assert N.tap(1, 2, 1).type is NoteType.TAP
    assert N.extap(1, 2, 1).type is NoteType.EXTAP
    assert N.flick(1, 2, 1).type is NoteType.FLICK
    assert N.damage(1, 2, 1).type is NoteType.DAMAGE
    assert N.hold_begin(1, 2, 1).type is NoteType.HOLD
    assert N.hold_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert N.hold_end(1, 2, 1).long_attr is LongAttr.END
    assert N.slide_begin(1, 2, 1).type is NoteType.SLIDE
    assert N.slide_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert N.air(1, 2, 1).type is NoteType.AIR
    assert N.air_slide_begin(1, 2, 1, 80).type is NoteType.AIRSLIDE
    assert N.air_hold_begin(1, 2, 1, 80).type is NoteType.AIRHOLD
    assert N.air_hold_begin(1, 2, 1, 80).long_attr is LongAttr.BEGIN
    assert N.air_hold_end(1, 2, 1, 80).long_attr is LongAttr.END
    crush0 = N.air_crush_begin(1, 2, 1, 80, 0)
    assert crush0.type is NoteType.AIRCRUSH
    assert crush0.long_attr is LongAttr.BEGIN
    assert crush0.option_value == 0
    head = N.air_crush_begin(1, 2, 1, 80, 0x7FFFFFFF)
    assert head.option_value == 0x7FFFFFFF
    assert N.air_crush_begin(1, 2, 1, 80, 120).option_value == 120


def test_air_crush_color_values_match_variation_ids():
    assert Color.DEFAULT == messages_pb2.COLOR_DEFAULT
    assert Color.RED == messages_pb2.COLOR_RED
    assert Color.ORANGE == messages_pb2.COLOR_ORANGE
    assert Color.YELLOW == messages_pb2.COLOR_YELLOW
    assert Color.GREEN == messages_pb2.COLOR_GREEN
    assert Color.SKY == messages_pb2.COLOR_SKY
    assert Color.BLUE == messages_pb2.COLOR_BLUE
    assert Color.VIOLET == messages_pb2.COLOR_VIOLET
    assert Color.PINK == messages_pb2.COLOR_PINK
    assert Color.WHITE == messages_pb2.COLOR_WHITE
    assert Color.BLACK == messages_pb2.COLOR_BLACK
    assert Color.GRASS == messages_pb2.COLOR_GRASS
    assert Color.SKY_BLUE == messages_pb2.COLOR_SKY_BLUE
    assert Color.COBALT_BLUE == messages_pb2.COLOR_COBALT_BLUE
    assert Color.PURPLE == messages_pb2.COLOR_PURPLE
    assert Color.NONE == messages_pb2.COLOR_NONE
    none = N.air_crush_begin(1, 2, 1, 80, 0, variation_id=Color.NONE)
    assert none.variation_id is Color.NONE
    assert none.to_proto().variation_id == 35


def test_note_enums_remain_public_exports():
    from margrete_rpc import (
        AirDirection,
        Color,
        ColorValue,
        Direction,
        ExAttr,
        ExtapDirection,
        FlickDirection,
        LongAttr,
        NoteType,
    )

    assert NoteType.TAP.value == messages_pb2.NOTE_TYPE_TAP
    assert LongAttr.END_NOACT.value == messages_pb2.LONG_ATTR_END_NOACT
    assert Direction.DOWN_RIGHT.value == messages_pb2.DIRECTION_DOWNRIGHT
    assert ExtapDirection.UP.value == "up"
    assert AirDirection.DOWN_RIGHT.value == "down_right"
    assert ExtapDirection.OUT_IN.value == "out_in"
    assert FlickDirection.RIGHT.value == "right"
    assert ExAttr.INVERT.value == messages_pb2.EX_ATTR_INVERT
    assert Color.NONE.value == messages_pb2.COLOR_NONE
    assert ColorValue.NONE == "none"


def test_air_crush_color_values_are_user_facing_strings():
    assert ColorValue.DEFAULT == "default"
    assert ColorValue.COBALT_BLUE == "cobalt_blue"


def test_direction_enum_values_are_user_facing_strings():
    assert AirDirection.UP == "up"
    assert AirDirection.UP_LEFT == "up_left"
    assert ExtapDirection.ROTATE_LEFT == "rotate_left"
    assert ExtapDirection.IN_OUT == "in_out"
    assert FlickDirection.AUTO == "auto"


def test_new_note_api_is_exported_from_root_package():
    from margrete_rpc import (
        TICKS_PER_BEAT,
        Air,
        AirCrush,
        AirHold,
        AirSlide,
        Hold,
        N,
        Node,
        NoopTracer,
        Note,
        NoteInfo,
        Slide,
        Tap,
        UnsupportedNoteTree,
        d2t,
    )

    assert N.tap(0, 4, 2).type is NoteType.TAP
    assert Node().info == NoteInfo()
    assert isinstance(Tap(0, 4, 2), Note)
    assert Hold is not None
    assert Slide is not None
    assert AirCrush is not None
    assert Air is not None
    assert AirSlide is not None
    assert AirHold is not None
    assert issubclass(UnsupportedNoteTree, ValueError)
    assert TICKS_PER_BEAT == 1920
    assert d2t(1, 4) == 480
    assert NoopTracer() is not None


def test_margrete_native_and_sdk_note_names_are_exported_from_root_package():
    from margrete_rpc import N, Node, Note

    assert N.tap(0, 4, 2).type is NoteType.TAP
    assert Node().info == NoteInfo()
    assert isinstance(Tap(0, 4, 2), Note)


def test_note_factories_require_geometry_and_specific_fields():
    with pytest.raises(TypeError):
        N.tap(t=1, x=2)
    with pytest.raises(TypeError):
        N.air_crush_begin(1, 2, 1)
    with pytest.raises(TypeError):
        N.air_slide_begin(1, 2, 1)
    with pytest.raises(TypeError):
        N.air_hold_begin(1, 2, 1)


def test_child_builds_long_note_chains():
    slide_begin = N.slide_begin(10, 0, 4)
    slide_step = N.slide_step(20, 6, 4)
    slide_end = N.slide_end(30, 12, 4)

    slide = slide_begin.child(slide_step, slide_end)

    assert slide is slide_begin
    assert slide.children == [slide_step, slide_end]

    hold_begin = N.hold_begin(40, 2, 4)
    hold_end = N.hold_end(50, 2, 4)
    assert hold_begin.child(hold_end) is hold_begin
    assert hold_begin.children == [hold_end]

    air_slide_begin = N.air_slide_begin(60, 4, 8, 80)
    air_slide_step = N.air_slide_step(70, 8, 8, 120)
    air_slide_end = N.air_slide_end(80, 12, 8, 80)
    assert air_slide_begin.child(air_slide_step, air_slide_end) is air_slide_begin
    assert air_slide_begin.children == [air_slide_step, air_slide_end]

    air_hold_begin = N.air_hold_begin(90, 4, 8, 80)
    air_hold_end = N.air_hold_end(100, 4, 8, 80)
    assert air_hold_begin.child(air_hold_end) is air_hold_begin
    assert air_hold_begin.children == [air_hold_end]

    air_crush_begin = N.air_crush_begin(110, 4, 8, 80, 5)
    air_crush_control = N.air_crush_control(120, 8, 8, 120, 0)
    air_crush_end = N.air_crush_end(130, 12, 8, 80, 0)
    assert air_crush_begin.child(air_crush_control, air_crush_end) is air_crush_begin
    assert air_crush_begin.children == [air_crush_control, air_crush_end]


def test_child_with_no_arguments_clears_children():
    note = N.tap(960, 4, 2, h=700)

    assert note.child() is note
    assert note.children == []


def test_child_adds_airlike_children_to_single_note():
    note = N.tap(960, 4, 2)
    air = N.air(960, 4, 2, direction=AirDirection.UP)
    air_slide = N.air_slide_begin(960, 4, 2, 80).child(
        N.air_slide_end(1440, 8, 2, 80),
    )

    assert note.child(air, air_slide) is note
    assert note.children == [air, air_slide]


def test_slide_segment_factories_match_long_attr():
    assert N.slide_step(10, 3, 1).long_attr is LongAttr.STEP
    assert N.slide_control(10, 3, 1).long_attr is LongAttr.CONTROL
    assert N.slide_curve_control(10, 3, 1).long_attr is LongAttr.CURVE_CONTROL
    assert N.slide_end(10, 3, 1).long_attr is LongAttr.END


def test_air_slide_segment_factories_match_long_attr():
    begin = N.air_slide_begin(11, 4, 1, 80)
    assert begin.long_attr is LongAttr.BEGIN
    assert N.air_slide_step(11, 4, 1, 80).long_attr is LongAttr.STEP
    assert N.air_slide_control(11, 4, 1, 80).long_attr is LongAttr.CONTROL
    assert N.air_slide_curve_control(11, 4, 1, 80).long_attr is LongAttr.CURVE_CONTROL
    assert N.air_slide_end(11, 4, 1, 80).long_attr is LongAttr.END
    assert N.air_slide_end_noact(11, 4, 1, 80).long_attr is LongAttr.END_NOACT


def test_air_hold_segment_factories_match_long_attr():
    assert N.air_hold_begin(11, 4, 1, 80).long_attr is LongAttr.BEGIN
    assert N.air_hold_step(11, 4, 1, 80).long_attr is LongAttr.STEP
    assert N.air_hold_end(11, 4, 1, 80).long_attr is LongAttr.END
    assert N.air_hold_end_noact(11, 4, 1, 80).long_attr is LongAttr.END_NOACT


def test_air_crush_segment_factories_match_long_attr():
    begin = N.air_crush_begin(11, 4, 1, 80, 5)
    assert begin.long_attr is LongAttr.BEGIN
    assert begin.option_value == 5
    assert N.air_crush_control(11, 4, 1, 80, 0).long_attr is LongAttr.CONTROL
    assert N.air_crush_end(11, 4, 1, 80, 0).long_attr is LongAttr.END


def test_note_defaults_and_tap_constructor_are_pythonic():
    note = N.tap(960, 4, 1)

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.NONE
    assert note.direction is Direction.UP
    assert note.to_proto().direction == messages_pb2.DIRECTION_UP
    assert note.ex_attr is ExAttr.NONE
    assert note.t == 960
    assert note.x == 4
    assert note.w == 1
    assert note.h == 800
    assert note._id is None
    assert note.children == []


def test_non_air_shape_factories_default_height_to_800():
    assert N.extap(1, 2, 1).h == 800
    assert N.flick(1, 2, 1).h == 800
    assert N.damage(1, 2, 1).h == 800
    assert N.hold_begin(1, 2, 1).h == 800
    assert N.slide_begin(1, 2, 1).h == 800
    assert N.air(1, 2, 1).h == 800


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
    note = Node(info=info, _id=12)

    assert note.type is NoteType.TAP
    assert note.long_attr is LongAttr.BEGIN
    assert note.direction is Direction.UP
    assert note.ex_attr is ExAttr.HAS_NOTE
    assert note.variation_id == 2
    assert note.t == 960
    assert note.x == 4
    assert note.w == 1
    assert note.h == 800
    assert note.til == 3
    assert note.option_value == 7
    assert note._id == 12


def test_event_dataclasses_accept_required_fields_as_positional_arguments():
    assert BpmEvent(0, 120.0) == BpmEvent(t=0, bpm=120.0)
    assert BeatEvent(0, 4, 4) == BeatEvent(
        bar=0,
        beats_per_bar=4,
        beat_unit=4,
    )
    assert TimelineSpeedEvent(2, 960, 0.75) == TimelineSpeedEvent(
        t=960,
        til=2,
        speed=0.75,
    )
    assert NoteSpeedEvent(960, 1.25) == NoteSpeedEvent(t=960, speed=1.25)


def test_node_tick_uses_int_and_d2t_for_fractions():
    note = N.tap(0, 4, 1)
    assert note.t == 0
    note.t = note.t + d2t(1, 8)
    assert note.t == 240
    note.t = note.t + d2t(1, 8)
    assert note.t == 480
    note.t = note.t - d2t(1, 4)
    assert note.t == 0


def test_node_tick_augmented_assignment_matches_direct_tick_math():
    note = N.tap(240, 4, 1)
    note.t = 480
    assert note.t == 480
    note.t = 1920
    assert note.t == 1920
    note.t = 300
    assert note.t == 300


def test_d2t_rejects_non_whole_tick():
    with pytest.raises(ValueError, match="whole tick"):
        d2t(1, 7)


def test_d2t_rejects_denominator_above_ticks_per_beat():
    with pytest.raises(ValueError, match="denominator must not exceed"):
        d2t(1, TICKS_PER_BEAT + 1)


def test_d2t_rejects_non_int_types():
    with pytest.raises(TypeError):
        d2t(1, 2.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        d2t("bad", 4)  # type: ignore[arg-type]


def test_note_and_node_tick_are_plain_int():
    note = N.tap(0, 4, 1)
    assert type(note.t) is int
    note.t = note.t + d2t(1, 8)
    assert note.info.t == 240

    tap = Tap(t=0, x=4, w=2)
    assert type(tap.t) is int
    tap.t = d2t(1, 4)
    assert tap.t == 480


def test_high_level_notes_accept_short_geometry_aliases():
    tap = Tap(t=(1, 0), x=4, w=2)
    assert tap.t == TICKS_PER_BEAT
    assert tap.t == TICKS_PER_BEAT
    assert tap.w == 2
    assert tap.w == 2

    tap.t = (0, 1)
    tap.w = 3
    assert tap.t == d2t(1, 4)
    assert tap.w == 3

    slide = Slide(t=0, x=4, w=2).step(t=480, x=6, w=3)
    assert slide.t == 0
    assert slide.w == 2
    assert slide.joints[0].t == 480
    assert slide.joints[0].w == 3


def test_air_notes_accept_short_height_aliases():
    air_slide = AirSlide(h=80).control(t=480, x=6, w=2, h=120)
    assert air_slide.h == 80
    assert air_slide.h == 80
    assert air_slide.joints[0].t == 480
    assert air_slide.joints[0].h == 120
    assert air_slide.joints[0].h == 120

    crush = AirCrush(t=0, x=4, w=2, h=80, density=5).control(t=480, x=6, w=3, h=120)
    assert crush.t == 0
    assert crush.w == 2
    assert crush.h == 80
    assert crush.joints[0].t == 480
    assert crush.joints[0].w == 3
    assert crush.joints[0].h == 120


def test_raw_note_api_accepts_short_geometry_aliases():
    note = N.tap(t=0, x=4, w=2, h=700, til=3)
    assert note.t == 0
    assert note.t == 0
    assert note.w == 2
    assert note.w == 2
    assert note.h == 700
    assert note.h == 700
    assert note.til == 3
    assert note.til == 3

    note.t = 480
    note.w = 3
    note.h = 800
    note.til = 4
    assert note.t == 480
    assert note.w == 3
    assert note.h == 800
    assert note.til == 4


def test_tick_subtracts_between_int_ticks():
    crush = AirCrush(t=100, x=4, w=2, h=80, density=5)
    crush.control(105, x=6, w=2, h=120).control(110, x=8, w=2, h=80)
    assert crush.joints[-1].t - crush.t == 10


def test_note_round_trips_to_protobuf_with_children_and_id():
    note = Node(
        _id=10,
        info=NoteInfo(
            type=NoteType.SLIDE,
            long_attr=LongAttr.BEGIN,
            direction=Direction.UP_LEFT,
            ex_attr=ExAttr.HAS_NOTE,
            variation_id=2,
            x=3,
            w=2,
            h=1,
            t=120,
            til=4,
            option_value=9,
        ),
        children=[N.tap(180, 5, 1)],
    )

    proto = note.to_proto()
    restored = Node.from_proto(proto)

    assert proto.id == 10
    assert proto.type == messages_pb2.NOTE_TYPE_SLIDE
    assert proto.long_attr == messages_pb2.LONG_ATTR_BEGIN
    assert restored == note


def test_node_info_properties_delegate_to_info():
    note = Node()

    note.type = NoteType.TAP
    note.long_attr = LongAttr.BEGIN
    note.direction = ExtapDirection.UP
    note.ex_attr = ExAttr.HAS_NOTE
    note.variation_id = 2
    note.x = 4
    note.w = 1
    note.h = 800
    note.t = 960
    note.til = 3
    note.option_value = 7

    assert note.info == NoteInfo(
        type=NoteType.TAP,
        long_attr=LongAttr.BEGIN,
        direction=Direction.UP,
        ex_attr=ExAttr.HAS_NOTE,
        variation_id=2,
        x=4,
        w=1,
        h=800,
        t=960,
        til=3,
        option_value=7,
    )


def test_l_factory_methods_build_low_level_notes():
    assert N.tap(1, 2, 1).type is NoteType.TAP
    assert N.extap(1, 2, 1).type is NoteType.EXTAP
    assert N.flick(1, 2, 1).type is NoteType.FLICK
    assert N.damage(1, 2, 1).type is NoteType.DAMAGE
    assert N.hold_begin(1, 2, 1).long_attr is LongAttr.BEGIN
    assert N.hold_end(2, 2, 1).long_attr is LongAttr.END
    assert N.slide_begin(1, 2, 1).type is NoteType.SLIDE
    assert N.air(1, 2, 1, direction=AirDirection.UP).direction is Direction.UP
    assert N.air_slide_end_noact(2, 4, 1, 80).long_attr is LongAttr.END_NOACT
    assert N.air_hold_end_noact(2, 4, 1, 80).long_attr is LongAttr.END_NOACT
    assert N.air_crush_begin(1, 2, 1, 80, 0x7FFFFFFF).option_value == 0x7FFFFFFF


def test_node_round_trips_to_protobuf_with_children_and_id():
    note = Node(
        _id=10,
        info=NoteInfo(
            type=NoteType.SLIDE,
            long_attr=LongAttr.BEGIN,
            direction=Direction.UP_LEFT,
            ex_attr=ExAttr.HAS_NOTE,
            variation_id=2,
            x=3,
            w=2,
            h=1,
            t=120,
            til=4,
            option_value=9,
        ),
        children=[N.tap(180, 5, 1)],
    )

    proto = note.to_proto()
    restored = Node.from_proto(proto)

    assert proto.id == 10
    assert proto.type == messages_pb2.NOTE_TYPE_SLIDE
    assert proto.long_attr == messages_pb2.LONG_ATTR_BEGIN
    assert restored == note


def test_tap_redirects_shared_mg_fields_and_converts_to_node():
    tap = Tap(t=960, x=4, w=2)
    tap.x = 5
    tap.til = 3
    tap._info.ex_attr = ExAttr.HAS_NOTE
    tap.t = 480

    node = tap.to_node()

    assert tap.t == 480
    assert tap.x == 5
    assert tap.w == 2
    assert tap.til == 3
    assert tap._info.ex_attr is ExAttr.HAS_NOTE
    assert node.type is NoteType.TAP
    assert node.long_attr is LongAttr.NONE
    assert node.t == 480
    assert node.x == 5
    assert node.w == 2
    assert node.til == 3
    assert node.ex_attr is ExAttr.HAS_NOTE
    assert node.children == []


def test_note_to_node_copies_note_info_instead_of_aliasing():
    tap = Tap(t=960, x=4, w=2)

    node = tap.to_node()
    node.t = 480
    node.x = 8

    assert tap.t == 960
    assert tap.x == 4


def test_high_level_ground_note_geometry_is_backed_by_note_info():
    extap = Extap(t=960, x=4, w=2, direction=ExtapDirection.UP)

    assert extap._info.t == 960
    assert extap._info.x == 4
    assert extap._info.w == 2
    assert extap._info.direction is Direction.UP

    extap.t = 480
    extap.x = 5
    extap.w = 3
    extap.direction = ExtapDirection.DOWN

    assert extap._info.t == 480
    assert extap._info.x == 5
    assert extap._info.w == 3
    assert extap._info.direction is Direction.DOWN

    extap._info.t = 240
    extap._info.x = 6
    extap._info.w = 4
    extap._info.direction = ExtapDirection.CENTER

    assert extap.t == 240
    assert extap.x == 6
    assert extap.w == 4
    assert extap.direction is ExtapDirection.CENTER


def test_tap_air_adds_single_air_child():
    tap = Tap(t=0, x=4, w=2)

    air = Air(AirDirection.DOWN)
    result = tap.air(air)
    node = tap.to_node()

    assert result is tap
    assert air.direction is AirDirection.DOWN
    assert len(node.children) == 1
    assert node.children[0].type is NoteType.AIR
    assert node.children[0].direction is Direction.DOWN
    assert node.children[0].t == tap.t
    assert node.children[0].x == tap.x
    assert node.children[0].w == tap.w


def test_air_replaces_existing_air_object():
    tap = Tap(t=0, x=4, w=2)
    first = Air(AirDirection.UP)
    second = Air(AirDirection.DOWN)

    assert tap.air(first).air(second) is tap
    assert tap.to_node().children[0].direction is Direction.DOWN


def test_air_direction_shorthand_attaches_plain_air():
    tap = Tap(t=0, x=4, w=2)

    assert tap.air(AirDirection.DOWN) is tap
    assert tap.to_node().children[0].direction is Direction.DOWN


def test_air_direction_string_shorthand_attaches_plain_air():
    tap = Tap(t=0, x=4, w=2)

    assert tap.air("down") is tap
    assert tap.to_node().children[0].direction is Direction.DOWN


def test_height_is_absent_from_floor_notes_and_bare_air():
    assert not hasattr(Tap(t=0, x=4, w=2), "height")
    assert not hasattr(Damage(t=0, x=4, w=2), "height")
    assert not hasattr(Slide(t=0, x=4, w=2), "height")
    assert not hasattr(Hold(t=0, x=4, w=2), "height")
    assert not hasattr(Air(AirDirection.UP), "height")
    assert not hasattr(AirSlide(h=80), "height")
    assert not hasattr(AirHold(h=80), "height")
    assert not hasattr(AirCrush(t=0, x=4, w=2, h=80, density=0), "height")
    assert hasattr(AirSlide(h=80), "h")
    assert hasattr(AirHold(h=80), "h")
    assert hasattr(AirCrush(t=0, x=4, w=2, h=80, density=0), "h")


def test_attachable_air_objects_are_not_placeable_notes():
    assert isinstance(Tap(t=0, x=4, w=2), Note)
    assert not isinstance(Air(AirDirection.UP), Note)
    assert not isinstance(AirSlide(h=80), Note)
    assert not isinstance(AirHold(h=80), Note)
    assert not hasattr(AirSlide(h=80), "to_node")
    assert not hasattr(AirHold(h=80), "to_node")
    assert not hasattr(AirCrush(t=0, x=4, w=2, h=80, density=0), "air")


def test_all_high_level_notes_expose_validate():
    notes = [
        Tap(t=0, x=4, w=2),
        Damage(t=0, x=4, w=2),
        Extap(t=0, x=4, w=2),
        Flick(t=0, x=4, w=2),
        Slide(t=0, x=4, w=2).step(960, x=4, w=2),
        Hold(t=0, x=4, w=2).step(960, x=4, w=2),
        AirCrush(t=0, x=4, w=2, h=80, density=5).control(960, x=4, w=2, h=80),
    ]

    for note in notes:
        note.validate()
        assert isinstance(note, Note)


def test_high_level_short_notes_validate_tick_and_width():
    with pytest.raises(ValueError, match="t must be non-negative"):
        Tap(t=-1, x=4, w=2)

    with pytest.raises(ValueError, match="w must be at least 1"):
        Tap(t=0, x=4, w=0)


def test_ground_note_validate_catches_invalid_mutated_info():
    tap = Tap(t=0, x=4, w=2)
    tap._info.w = 0

    with pytest.raises(ValueError, match="w must be at least 1"):
        tap.validate()

    with pytest.raises(ValueError, match="w must be at least 1"):
        tap.to_node()


def test_ground_note_direction_is_available_only_on_extap_and_flick():
    tap = Tap(t=0, x=4, w=2)
    damage = Damage(t=0, x=4, w=2)

    assert not hasattr(tap, "direction")
    assert not hasattr(damage, "direction")
    assert Extap(t=0, x=4, w=2).direction is ExtapDirection.UP
    assert Flick(t=0, x=4, w=2).direction is FlickDirection.AUTO


@pytest.mark.parametrize(
    "direction",
    [
        ExtapDirection.UP,
        ExtapDirection.DOWN,
        ExtapDirection.CENTER,
        ExtapDirection.LEFT,
        ExtapDirection.RIGHT,
        ExtapDirection.ROTATE_LEFT,
        ExtapDirection.ROTATE_RIGHT,
        ExtapDirection.IN_OUT,
        ExtapDirection.OUT_IN,
    ],
)
def test_extap_accepts_only_extap_directions(direction):
    extap = Extap(t=0, x=4, w=2, direction=direction)

    assert extap.direction is direction

    extap.direction = direction
    assert extap._info.direction is Direction[direction.name]


def test_extap_accepts_string_direction_and_serializes_to_proto_value():
    extap = Extap(t=0, x=4, w=2, direction="rotate_left")

    assert extap.direction is ExtapDirection.ROTATE_LEFT
    assert extap.direction == "rotate_left"

    extap.direction = "in_out"
    assert extap.direction is ExtapDirection.IN_OUT
    assert extap.to_node().to_proto().direction == messages_pb2.DIRECTION_INOUT


@pytest.mark.parametrize(
    "direction",
    [
        messages_pb2.DIRECTION_NONE,
        messages_pb2.DIRECTION_AUTO,
        messages_pb2.DIRECTION_UPLEFT,
    ],
)
def test_extap_rejects_invalid_directions(direction):
    with pytest.raises(ValueError, match="invalid extap direction"):
        Extap(t=0, x=4, w=2, direction=direction)

    extap = Extap(t=0, x=4, w=2)
    with pytest.raises(ValueError, match="invalid extap direction"):
        extap.direction = direction


@pytest.mark.parametrize(
    "direction", [FlickDirection.AUTO, FlickDirection.LEFT, FlickDirection.RIGHT]
)
def test_flick_accepts_only_flick_directions(direction):
    flick = Flick(t=0, x=4, w=2, direction=direction)

    assert flick.direction is direction

    flick.direction = direction
    assert flick._info.direction is Direction[direction.name]


def test_flick_accepts_string_direction_and_serializes_to_proto_value():
    flick = Flick(t=0, x=4, w=2, direction="left")

    assert flick.direction is FlickDirection.LEFT
    assert flick.direction == "left"
    assert flick.to_node().to_proto().direction == messages_pb2.DIRECTION_LEFT


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
        Flick(t=0, x=4, w=2, direction=direction)

    flick = Flick(t=0, x=4, w=2)
    with pytest.raises(ValueError, match="invalid flick direction"):
        flick.direction = direction


@pytest.mark.parametrize(
    "direction",
    [
        AirDirection.UP,
        AirDirection.DOWN,
        AirDirection.UP_LEFT,
        AirDirection.UP_RIGHT,
        AirDirection.DOWN_LEFT,
        AirDirection.DOWN_RIGHT,
    ],
)
def test_air_accepts_only_air_directions(direction):
    air = Air(direction)

    assert air.direction is direction

    air.direction = direction
    assert air._info.direction is Direction[direction.name]


def test_air_accepts_string_direction_and_serializes_to_proto_value():
    air = Air("up_left")

    assert air.direction is AirDirection.UP_LEFT
    assert air.direction == "up_left"

    air.direction = "down_right"
    assert air.direction is AirDirection.DOWN_RIGHT
    assert air._to_node(NoteInfo()).to_proto().direction == messages_pb2.DIRECTION_DOWNRIGHT


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
    with pytest.raises(ValueError, match="invalid air direction"):
        Air(direction)

    air = Air(AirDirection.UP)
    with pytest.raises(ValueError, match="invalid air direction"):
        air.direction = direction


def test_slide_promotes_last_joint_to_end_and_preserves_partial_debug_tree():
    slide = Slide(t=960, x=0, w=4).step(1440, x=6, w=4).control(1680, x=8, w=4)

    partial = slide.to_node(skip_validation=True)
    assert partial.type is NoteType.SLIDE
    assert [c.long_attr for c in partial.children] == [
        LongAttr.STEP,
        LongAttr.CONTROL,
    ]

    node = slide.to_node()

    assert node.type is NoteType.SLIDE
    assert node.long_attr is LongAttr.BEGIN
    assert [child.long_attr for child in node.children] == [
        LongAttr.STEP,
        LongAttr.END,
    ]


def test_long_note_requires_at_least_one_serializable_joint():
    with pytest.raises(ValueError, match="requires at least one joint"):
        Slide(t=960, x=0, w=4).to_node()

    with pytest.raises(ValueError, match="requires at least one joint"):
        AirCrush(t=0, x=4, w=2, h=80, density=5).to_node()


def test_long_note_validate_catches_invalid_begin_geometry():
    slide = Slide(t=0, x=4, w=2).step(960, x=4, w=2)
    slide._info.w = 0

    with pytest.raises(ValueError, match="w must be at least 1"):
        slide.validate()

    with pytest.raises(ValueError, match="w must be at least 1"):
        slide.to_node()


def test_note_validate_catches_invalid_attached_air_builder():
    tap = Tap(t=0, x=4, w=2).air(AirSlide(h=80))

    with pytest.raises(ValueError, match="requires at least one joint"):
        tap.validate()

    with pytest.raises(ValueError, match="requires at least one joint"):
        tap.to_node()


def test_note_validate_checks_attached_air_against_anchor_tick():
    tap = Tap(t=1000, x=4, w=2).air(AirSlide(h=80).step(960, x=4, w=2, h=80))

    with pytest.raises(ValueError, match="joint t must be later than previous joint"):
        tap.validate()

    with pytest.raises(ValueError, match="joint t must be later than previous joint"):
        tap.to_node()


def test_debug_str_matches_repr_and_includes_tick_and_enum_name_value():
    tap = Tap(t=1920, x=1, w=2)
    assert str(tap) == repr(tap)
    assert "Tap(" in str(tap)
    assert "t=1920" in str(tap)
    node = N.tap(1920, 1, 2)
    assert str(node) == repr(node)
    assert "t=1920" in str(node)
    assert "NoteType.TAP(" in str(node) and ")" in str(node)


def test_high_level_str_prints_attached_air_as_children():
    tap = Tap(t=0, x=4, w=2)
    tap.air(AirSlide(h=80).step(960, x=8, w=2, h=100))

    lines = str(tap).splitlines()

    assert lines[0].startswith("Tap(")
    assert lines[1].startswith("  AirSlide(")
    assert "air=" not in lines[0]
    assert "long_action=" not in lines[1]


def test_slide_rejects_non_increasing_ticks():
    slide = Slide(t=960, x=0, w=4)

    with pytest.raises(ValueError, match="must be later"):
        slide.step(960, x=6, w=4)


def test_hold_step_promotes_to_end_with_explicit_geometry():
    hold = Hold(t=0, x=4, w=2)
    node = hold.step(960, x=4, w=2).to_node()

    assert node.type is NoteType.HOLD
    assert len(node.children) == 1
    assert node.children[0].long_attr is LongAttr.END
    assert node.children[0].x == 4
    assert node.children[0].w == 2


def test_hold_has_a_single_end_and_step_replaces_it():
    hold = Hold(t=0, x=4, w=2).step(960, x=4, w=2).step(1920, x=6, w=2)
    node = hold.to_node()

    assert len(node.children) == 1
    assert node.children[0].long_attr is LongAttr.END
    assert node.children[0].t == 1920
    assert node.children[0].x == 6

    with pytest.raises(ValueError, match="must be later"):
        Hold(t=1000, x=4, w=2).step(2000, x=4, w=2).step(1000, x=4, w=2)


def test_slide_joints_use_explicit_geometry():
    slide = Slide(t=0, x=4, w=2).control(480, 5, 2).step(960, 6, 3)
    with pytest.deprecated_call():
        slide.curve_control(1440, 7, 4)
    slide.step(1920, 8, 5)

    node = slide.to_node()

    assert [child.long_attr for child in node.children] == [
        LongAttr.CONTROL,
        LongAttr.STEP,
        LongAttr.CURVE_CONTROL,
        LongAttr.END,
    ]
    assert [(child.x, child.w, child.h) for child in node.children] == [
        (5, 2, 800),
        (6, 3, 800),
        (7, 4, 800),
        (8, 5, 800),
    ]


def test_joint_kind_is_public_editable_property():
    slide = Slide(t=0, x=4, w=2).control(480, x=4, w=2).step(960, x=4, w=2)

    assert slide.joints[0].kind is JointKind.CONTROL
    slide.joints[0].kind = "step"

    node = slide.to_node()

    assert slide.joints[0].kind is JointKind.STEP
    assert [child.long_attr for child in node.children] == [LongAttr.STEP, LongAttr.END]


def test_joint_does_not_keep_public_proto_names():
    joint = Joint(t=960, x=8, w=2, kind=JointKind.STEP)

    assert not hasattr(joint, "long_attr")
    assert not hasattr(joint, "type")
    assert not hasattr(joint, "info")
    with pytest.raises(TypeError):
        Joint(t=960, x=8, w=2, long_attr=LongAttr.STEP)


def test_public_joints_list_can_be_mutated_and_validated():
    slide = Slide(t=0, x=4, w=2)
    slide.joints.append(Joint(t=960, x=8, w=2, kind="step"))

    slide.validate()
    node = slide.to_node()

    assert len(node.children) == 1
    assert node.children[0].long_attr is LongAttr.END
    assert node.children[0].x == 8

    slide.joints.append("bad")
    with pytest.raises(TypeError, match="joint"):
        slide.validate()


def test_public_joints_list_rejects_wrong_joint_shape():
    slide = Slide(t=0, x=4, w=2)
    slide.joints.append(AirJoint(t=960, x=8, w=2, h=80, kind="step"))

    with pytest.raises(TypeError, match="Joint"):
        slide.validate()

    tap = Tap(t=0, x=4, w=2).air(AirSlide(h=80))
    air_slide = tap._air
    assert isinstance(air_slide, AirSlide)
    air_slide.joints.append(Joint(t=960, x=8, w=2, kind="step"))

    with pytest.raises(TypeError, match="AirJoint"):
        tap.validate()


def test_air_long_joints_use_explicit_geometry():
    slide_tap = Tap(t=0, x=4, w=2).air(AirSlide(h=80).control(480, 4, 2, 80).step(960, 5, 2, 90))
    air_slide = slide_tap._air
    assert isinstance(air_slide, AirSlide)
    with pytest.deprecated_call():
        air_slide.curve_control(1440, 6, 2, 100)
    air_slide.control(1920, 7, 2, 110)
    assert all(isinstance(joint, AirJoint) for joint in air_slide.joints)
    hold_tap = Tap(t=0, x=6, w=2).air(AirHold(h=120).step(480, 6, 2, 120).control(960, 7, 2, 130))

    slide_node = slide_tap.to_node().children[0].children[0]
    hold_node = hold_tap.to_node().children[0].children[0]

    assert [(child.x, child.w, child.h) for child in slide_node.children] == [
        (4, 2, 80),
        (5, 2, 90),
        (6, 2, 100),
        (7, 2, 110),
    ]
    assert [(child.x, child.w, child.h) for child in hold_node.children] == [
        (6, 2, 120),
        (7, 2, 130),
    ]


def test_air_crush_joints_use_explicit_geometry():
    crush = (
        AirCrush(t=0, x=4, w=2, h=80, density=0)
        .control(480, x=4, w=2, h=80)
        .control(960, x=6, w=3, h=100)
    )

    node = crush.to_node()

    assert all(isinstance(joint, AirJoint) for joint in crush.joints)
    assert [(child.long_attr, child.x, child.w, child.h) for child in node.children] == [
        (LongAttr.CONTROL, 4, 2, 80),
        (LongAttr.END, 6, 3, 100),
    ]


def test_air_slide_forces_upward_air_and_promotes_control_to_end_noact():
    tap = Tap(t=0, x=4, w=2).air(
        AirSlide(h=80).control(480, x=6, w=2, h=120).control(960, x=8, w=2, h=80)
    )

    node = tap.to_node()

    air = node.children[0]
    air_long = air.children[0]
    assert air.direction is Direction.UP
    assert air_long.type is NoteType.AIRSLIDE
    assert air_long.children[-1].long_attr is LongAttr.END_NOACT


def test_control_terminus_differs_between_air_slide_and_ground_slide():
    air_slide = Tap(t=0, x=4, w=2).air(AirSlide(h=80).control(480, x=4, w=2, h=80))
    slide = Slide(t=0, x=4, w=2).control(480, x=4, w=2)

    air_slide_node = air_slide.to_node().children[0].children[0]
    slide_node = slide.to_node()

    assert air_slide_node.children[-1].long_attr is LongAttr.END_NOACT
    assert slide_node.children[-1].long_attr is LongAttr.END


def test_air_hold_has_no_curve_control_but_air_slide_does():
    assert hasattr(AirSlide(h=80), "curve_control")
    assert not hasattr(AirHold(h=80), "curve_control")
    assert hasattr(AirHold(h=80), "control")


def test_air_invert_maps_to_ex_attr_invert_on_ll():
    tap = Tap(t=0, x=4, w=2)
    air = Air(AirDirection.DOWN)
    tap.air(air)
    air.inverted = True
    air.til = 3
    tap.t = tap.t + d2t(1, 4)

    node = tap.to_node().children[0]

    assert air.inverted is True
    assert node.ex_attr is ExAttr.INVERT
    assert node.til == 3
    assert node.t == 480


def test_air_geometry_is_derived_from_anchor_on_serialization():
    tap = Tap(t=0, x=4, w=2).air(Air(AirDirection.DOWN))
    air = tap._air

    assert isinstance(air, Air)
    assert air._info.direction is Direction.DOWN

    tap.t = 480
    tap.x = 5
    tap.w = 3
    air.direction = AirDirection.UP

    node = tap.to_node().children[0]

    assert air._info.direction is Direction.UP
    assert node.t == 480
    assert node.x == 5
    assert node.w == 3
    assert node.direction is Direction.UP


def test_air_slide_and_air_hold_do_not_expose_color_on_note_builder():
    tap = Tap(t=0, x=4, w=2).air(AirSlide(h=80).step(960, x=8, w=2, h=100))
    hold = Tap(t=1200, x=4, w=2).air(AirHold(h=120).control(1680, x=4, w=2, h=140))

    assert tap.to_node().children[0].children[0].variation_id == 0
    assert hold.to_node().children[0].children[0].variation_id == 0


def test_air_crush_allows_controls_and_promotes_last_to_end():
    crush = AirCrush(t=0, x=4, w=2, h=80, density=5)

    node = crush.control(480, x=6, w=2, h=120).control(960, x=8, w=2, h=80).to_node()

    assert node.type is NoteType.AIRCRUSH
    assert [child.long_attr for child in node.children] == [LongAttr.CONTROL, LongAttr.END]


def test_air_crush_density_and_color_redirect_to_node_storage_fields():
    crush = AirCrush(
        t=0,
        x=4,
        w=2,
        h=80,
        density=0,
        color=Color.RED,
    )
    crush.density = 120
    crush.color = Color.NONE
    crush.til = 2
    node = crush.control(960, x=8, w=2, h=100).to_node()

    assert crush.density == 120
    assert crush.color is ColorValue.NONE
    assert node.option_value == 120
    assert node.variation_id == Color.NONE
    assert node.til == 2
    assert node.children[0].option_value == 0


def test_air_crush_density_is_plain_int():
    crush = AirCrush(t=0, x=4, w=2, h=80, density=0)
    crush.density = d2t(1, 8)
    assert crush.density == 240
    assert type(crush.density) is int
    crush.density = crush.density + d2t(1, 8)
    assert crush.density == 480


def test_wrap_node_supports_air_hold_with_steps_attached_to_air():
    node = N.tap(19200, 4, 8).child(
        N.air(19200, 4, 8, direction=AirDirection.UP).child(
            N.air_hold_begin(19200, 4, 8, 80).child(
                N.air_hold_step(19680, 4, 8, 800),
                N.air_hold_end(20160, 4, 8, 800),
            )
        )
    )

    wrapped = wrap_node(node)
    restored = wrapped.to_node()

    assert restored == node


def test_long_note_begin_geometry_is_backed_by_note_info():
    slide = Slide(t=960, x=0, w=4)

    assert slide._info.t == 960
    assert slide._info.x == 0
    assert slide._info.w == 4
    assert slide._info.h == 800

    slide.t = 480
    slide.x = 2
    slide.w = 3

    assert slide._info.t == 480
    assert slide._info.x == 2
    assert slide._info.w == 3

    slide._info.t = 240
    slide._info.x = 1
    slide._info.w = 2
    slide._info.h = 600

    assert slide.t == 240
    assert slide.x == 1
    assert slide.w == 2


def test_long_note_joint_geometry_is_backed_by_internal_storage_without_proto_kind():
    slide = Slide(t=960, x=0, w=4).step(1440, x=6, w=3)
    joint = slide.joints[0]

    assert not hasattr(joint, "info")
    assert joint.t == 1440
    assert joint.x == 6
    assert joint.w == 3
    assert not hasattr(joint, "h")
    assert joint.kind is JointKind.STEP

    joint.t = 1680
    joint.x = 7
    joint.w = 2
    joint.kind = JointKind.CONTROL

    assert joint.t == 1680
    assert joint.x == 7
    assert joint.w == 2
    assert joint.kind is JointKind.CONTROL


def test_long_note_exposes_joints_for_iteration():
    slide = Slide(t=960, x=0, w=4).step(1440, x=6, w=3).step(1920, x=12, w=4)

    assert slide.joints is slide._joints
    assert [joint.kind for joint in slide.joints] == [
        JointKind.STEP,
        JointKind.STEP,
    ]
    assert slide.joints[-1].t == 1920


def test_wrapped_long_note_joint_info_redirects_and_preserves_metadata():
    node = N.slide_begin(960, 0, 4).child(
        N.slide_step(1440, 6, 3, til=2, ex_attr=ExAttr.HAS_NOTE),
        N.slide_end(1920, 12, 4),
    )

    wrapped = wrap_node(node)
    joint = wrapped.joints[0]
    joint.t = 1680
    restored = wrapped.to_node()

    assert isinstance(wrapped, Slide)
    assert restored.children[0].t == 1680
    assert restored.children[0].til == 2
    assert restored.children[0].ex_attr is ExAttr.HAS_NOTE


def test_wrap_node_wraps_tap_and_preserves_noop_info():
    node = N.tap(240, 1, 2, h=123, til=4)

    wrapped = wrap_node(node)
    wrapped.x = 5
    restored = wrapped.to_node()

    assert isinstance(wrapped, Tap)
    assert restored.x == 5
    assert restored.h == 123
    assert restored.til == 4


def test_wrap_node_wraps_slide_with_ordered_joints():
    node = N.slide_begin(960, 0, 4, til=2).child(
        N.slide_step(1440, 6, 4),
        N.slide_control(1680, 8, 4),
        N.slide_end(1920, 12, 4),
    )

    wrapped = wrap_node(node)
    restored = wrapped.to_node()

    assert isinstance(wrapped, Slide)
    assert restored == node


def test_wrap_node_rejects_invalid_begin_end_placement():
    invalid = N.slide_begin(960, 0, 4).child(
        N.slide_step(1440, 6, 4),
        N.slide_control(1200, 8, 4),
        N.slide_end(1920, 12, 4),
    )

    with pytest.raises(UnsupportedNoteTree):
        wrap_node(invalid)


def test_wrap_node_rejects_air_on_non_end_slide_joint():
    invalid = N.slide_begin(960, 0, 4).child(
        N.slide_step(1440, 6, 4).child(N.air(1440, 6, 4, direction=AirDirection.UP)),
        N.slide_end(1920, 12, 4),
    )

    with pytest.raises(UnsupportedNoteTree):
        wrap_node(invalid)


def test_wrap_node_rejects_many_air_children():
    invalid = N.tap(0, 4, 2).child(
        N.air(0, 4, 2, direction=AirDirection.UP),
        N.air(0, 4, 2, direction=AirDirection.DOWN),
    )

    with pytest.raises(UnsupportedNoteTree):
        wrap_node(invalid)


def test_wrap_node_preserves_raw_extap_none_direction():
    node = N.extap(0, 4, 2, direction=messages_pb2.DIRECTION_NONE)

    wrapped = wrap_node(node)
    restored = wrapped.to_node()

    assert isinstance(wrapped, Extap)
    assert wrapped.direction == messages_pb2.DIRECTION_NONE
    assert restored == node


def test_wrap_node_preserves_transformed_extap_direction_with_air():
    node = N.extap(
        79200,
        8,
        4,
        h=80,
        direction=messages_pb2.DIRECTION_AUTO,
    ).child(
        N.air(
            79200,
            8,
            4,
            h=80,
            direction=AirDirection.DOWN_RIGHT,
        )
    )
    node._id = 1103
    node.children[0]._id = 1104

    wrapped = wrap_node(node)
    restored = wrapped.to_node()

    assert isinstance(wrapped, Extap)
    assert wrapped.direction == messages_pb2.DIRECTION_AUTO
    assert restored == node


@pytest.mark.parametrize(
    "direction",
    [
        messages_pb2.DIRECTION_ROTATE_LEFT,
        messages_pb2.DIRECTION_INOUT,
    ],
)
def test_wrap_node_preserves_transformed_flick_direction(direction):
    node = N.flick(153440, 2, 12, h=80, direction=direction).child(
        N.air(
            153440,
            2,
            12,
            h=80,
            direction=AirDirection.UP_RIGHT,
            ex_attr=ExAttr.INVERT,
        )
    )

    wrapped = wrap_node(node)
    restored = wrapped.to_node()

    assert isinstance(wrapped, Flick)
    assert wrapped.direction == direction
    assert restored == node


def test_chart_from_begin_edit_response_splits_wrapped_and_nodes():
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
    assert len(chart.nodes) == 1
    assert chart.nodes[0]._id == 2
    assert chart.events.bpm == [BpmEvent(0, 120.0)]


def test_chart_from_begin_edit_response_preserves_raw_extap_none_direction():
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
    assert chart.nodes == []
    assert isinstance(chart.notes[0], Extap)
    assert chart.notes[0].direction == messages_pb2.DIRECTION_NONE


def test_event_normalization_uses_last_write_wins_by_key():
    chart = Chart(
        events=ChartEvents(
            bpm=[BpmEvent(0, 120.0), BpmEvent(0, 180.0)],
            beat=[
                BeatEvent(bar=0, beats_per_bar=3, beat_unit=4),
                BeatEvent(bar=0, beats_per_bar=4, beat_unit=4),
            ],
            til=[
                TimelineSpeedEvent(t=960, til=1, speed=0.5),
                TimelineSpeedEvent(t=960, til=1, speed=0.75),
            ],
            note_speed=[NoteSpeedEvent(480, 1.5), NoteSpeedEvent(480, 1.25)],
        ),
    )

    normalized = normalize_event_operations(chart)

    assert normalized.events.bpm == [BpmEvent(0, 180.0)]
    assert normalized.events.beat == [BeatEvent(0, 4, 4)]
    assert normalized.events.til == [TimelineSpeedEvent(1, 960, 0.75)]
    assert normalized.events.note_speed == [NoteSpeedEvent(480, 1.25)]
