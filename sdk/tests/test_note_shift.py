import copy

from margrete_rpc import (
    AirCrush,
    AirCrushColor,
    AirDirection,
    Hold,
    L,
    LLNote,
    NoteType,
    Slide,
    Tap,
)
from margrete_rpc.model.note import wrap_ll_note


def _collect_geometry(note: LLNote) -> list[tuple[int, int, int, int]]:
    rows = [(int(note.tick), note.x, note.width, note.height)]
    for child in note.children:
        rows.extend(_collect_geometry(child))
    return rows


def test_llnote_shift_moves_root_and_nested_children():
    tree = L.tap(100, 4, 2).child(
        L.air(100, 4, 2, height=50).child(L.air_slide_begin(100, 4, 2, 40))
    )
    tree.shift(t=5, x=1, w=2, h=10)
    assert _collect_geometry(tree) == [
        (105, 5, 4, 810),
        (105, 5, 4, 60),
        (105, 5, 4, 50),
    ]


def test_llnote_shift_noop_when_all_zero():
    note = L.tap(10, 4, 2)
    before = note.info
    assert note.shift() is note
    assert note.info is before
    assert note.tick == 10


def test_hl_ground_with_air_and_air_slide_shifts_all_nodes():
    tap = Tap(tick=100, x=4, width=2)
    tap.air(AirDirection.DOWN).slide(height=80).end(200, x=8, width=2, height=100)

    tap.shift(t=5, h=10)

    assert tap.tick == 105
    assert tap.height == 90
    air = tap._air
    assert air.tick == 105
    assert air.height == 90
    slide = air._long_action
    assert slide.tick == 105
    assert slide.height == 90
    assert slide.joints[-1].tick == 205
    assert slide.joints[-1].height == 110


def test_hl_slide_shifts_begin_and_all_joints():
    slide = Slide(tick=100, x=0, width=4, height=80).step(150, x=2, width=4).end(200, x=4, width=4)
    slide.shift(t=10, x=1, w=1, h=5)
    assert slide.tick == 110
    assert slide.x == 1
    assert slide.width == 5
    assert slide.height == 85
    assert slide.joints[0].tick == 160
    assert slide.joints[0].x == 3
    assert slide.joints[1].tick == 210
    assert slide.joints[1].x == 5


def test_hl_hold_and_slide_joint_air_shift():
    hold = Hold(tick=50, x=1, width=3, height=70).end(120)
    hold.air(AirDirection.UP)
    hold.shift(t=3)

    assert hold.tick == 53
    end = hold.joints[-1]
    assert end.tick == 123
    assert end.air.tick == 123

    slide = Slide(tick=10, x=0, width=2, height=80).end(30, x=4, width=2)
    slide.air(AirDirection.DOWN)
    slide.shift(h=20)
    assert slide.height == 100
    assert slide.joints[-1].air.height == 100


def test_hl_air_crush_shifts_begin_controls_and_end():
    crush = (
        AirCrush(tick=0, x=1, width=2, height=80, density=5, color=AirCrushColor.RED)
        .control(50, x=2, width=2, height=90)
        .end(100, x=3, width=2, height=70)
    )
    crush.shift(t=7, h=3)
    assert crush.tick == 7
    assert crush.height == 83
    assert crush.joints[0].tick == 57
    assert crush.joints[0].height == 93
    assert crush.joints[1].tick == 107
    assert crush.joints[1].height == 73
    assert crush.density == 5
    assert crush.color is AirCrushColor.RED


def test_hl_shift_then_to_ll_matches_ll_shift_on_wrapped_tree():
    tap = Tap(tick=100, x=4, width=2)
    tap.air(AirDirection.DOWN).slide(height=80).end(200, x=8, width=2, height=100)

    hl_path = copy.deepcopy(tap)
    hl_path.shift(t=5, x=1, w=0, h=10)
    hl_geom = _collect_geometry(hl_path.to_ll(skip_validation=True))

    ll_path = wrap_ll_note(tap.to_ll(skip_validation=True))
    ll_path.shift(t=5, x=1, w=0, h=10)
    ll_geom = _collect_geometry(ll_path.to_ll(skip_validation=True))

    assert hl_geom == ll_geom


def test_shift_chaining_returns_same_object_and_composes():
    tap = Tap(tick=10, x=4, width=2)
    result = tap.shift(t=5).shift(x=2)
    assert result is tap
    assert tap.tick == 15
    assert tap.x == 6


def test_shift_does_not_validate_negative_tick_or_width():
    tap = Tap(tick=5, x=0, width=2)
    tap.shift(t=-10_000, w=-5)
    assert tap.tick == -9995
    assert tap.width == -3


def test_shift_preserves_id_and_timeline_id():
    note = L.tap(1, 2, 1, timeline_id=42)
    note.id = 99
    note.shift(t=3)
    assert note.id == 99
    assert note.timeline_id == 42
    assert note.type is NoteType.TAP
