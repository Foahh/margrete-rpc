import copy

from margrete_rpc import (
    Air,
    AirCrush,
    AirCrushColor,
    AirDirection,
    AirHold,
    AirSlide,
    Hold,
    N,
    Node,
    NoteType,
    Slide,
    Tap,
)
from margrete_rpc.chart.note import wrap_node


def _collect_geometry(note: Node) -> list[tuple[int, int, int, int]]:
    rows = [(int(note.t), note.x, note.w, note.h)]
    for child in note.children:
        rows.extend(_collect_geometry(child))
    return rows


def test_node_shift_moves_root_and_nested_children():
    tree = N.tap(100, 4, 2).child(N.air(100, 4, 2, h=50).child(N.air_slide_begin(100, 4, 2, 40)))
    tree.shift(t=5, x=1, w=2, h=10)
    assert _collect_geometry(tree) == [
        (105, 5, 4, 810),
        (105, 5, 4, 60),
        (105, 5, 4, 50),
    ]


def test_node_shift_noop_when_all_zero():
    note = N.tap(10, 4, 2)
    before = note.info
    assert note.shift() is note
    assert note.info is before
    assert note.t == 10


def test_note_ground_with_air_and_air_slide_shifts_all_nodes():
    tap = Tap(t=100, x=4, w=2).air(AirSlide(h=80).step(200, x=8, w=2, h=100))

    tap.shift(t=5, h=10)

    assert tap.t == 105
    air = tap._air
    assert isinstance(air, AirSlide)
    assert air.h == 90
    assert air._air_info.h == 90
    assert air.joints[-1].t == 205
    assert air.joints[-1].h == 110


def test_note_slide_shifts_begin_and_all_joints():
    slide = Slide(t=100, x=0, w=4).step(150, x=2, w=4).step(200, x=4, w=4)
    slide.shift(t=10, x=1, w=1, h=5)
    assert slide.t == 110
    assert slide.x == 1
    assert slide.w == 5
    assert slide._info.h == 805
    assert slide.joints[0].t == 160
    assert slide.joints[0].x == 3
    assert slide.joints[1].t == 210
    assert slide.joints[1].x == 5


def test_note_hold_and_slide_air_shift():
    hold = Hold(t=50, x=1, w=3).step(120).air(AirHold(h=70).step(160))
    hold.shift(t=3)

    assert hold.t == 53
    end = hold.joints[-1]
    assert end.t == 123
    assert isinstance(hold._air, AirHold)
    assert hold._air.joints[-1].t == 163

    slide = Slide(t=10, x=0, w=2).step(30, x=4, w=2).air(AirDirection.DOWN)
    slide.shift(h=20)
    assert slide._info.h == 820
    assert isinstance(slide._air, Air)


def test_note_air_crush_shifts_begin_controls_and_end():
    crush = (
        AirCrush(t=0, x=1, w=2, h=80, density=5, color=AirCrushColor.RED)
        .control(50, x=2, w=2, h=90)
        .control(100, x=3, w=2, h=70)
    )
    crush.shift(t=7, h=3)
    assert crush.t == 7
    assert crush.h == 83
    assert crush.joints[0].t == 57
    assert crush.joints[0].h == 93
    assert crush.joints[1].t == 107
    assert crush.joints[1].h == 73
    assert crush.density == 5
    assert crush.color is AirCrushColor.RED


def test_note_shift_then_to_node_matches_node_shift_on_wrapped_tree():
    tap = Tap(t=100, x=4, w=2).air(AirSlide(h=80).step(200, x=8, w=2, h=100))

    note_path = copy.deepcopy(tap)
    note_path.shift(t=5, x=1, w=0, h=10)
    note_geom = _collect_geometry(note_path.to_node())

    node_path = wrap_node(tap.to_node())
    node_path.shift(t=5, x=1, w=0, h=10)
    node_geom = _collect_geometry(node_path.to_node())

    assert note_geom == node_geom


def test_shift_chaining_returns_same_object_and_composes():
    tap = Tap(t=10, x=4, w=2)
    result = tap.shift(t=5).shift(x=2)
    assert result is tap
    assert tap.t == 15
    assert tap.x == 6


def test_shift_does_not_validate_negative_tick_or_width():
    tap = Tap(t=5, x=0, w=2)
    tap.shift(t=-10_000, w=-5)
    assert tap.t == -9995
    assert tap.w == -3


def test_shift_preserves_id_and_timeline_id():
    note = N.tap(1, 2, 1, til=42)
    note._id = 99
    note.shift(t=3)
    assert note._id == 99
    assert note.til == 42
    assert note.type is NoteType.TAP
