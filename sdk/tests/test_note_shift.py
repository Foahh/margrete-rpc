import copy

from margrete_rpc import (
    Air,
    AirCrush,
    AirCrushColor,
    AirDirection,
    AirHold,
    AirSlide,
    Hold,
    M,
    MgNote,
    NoteType,
    Slide,
    Tap,
)
from margrete_rpc.model.note import wrap_mg_note


def _collect_geometry(note: MgNote) -> list[tuple[int, int, int, int]]:
    rows = [(int(note.tick), note.x, note.width, note.height)]
    for child in note.children:
        rows.extend(_collect_geometry(child))
    return rows


def test_mgnote_shift_moves_root_and_nested_children():
    tree = M.tap(100, 4, 2).child(
        M.air(100, 4, 2, height=50).child(M.air_slide_begin(100, 4, 2, 40))
    )
    tree.shift(t=5, x=1, w=2, h=10)
    assert _collect_geometry(tree) == [
        (105, 5, 4, 810),
        (105, 5, 4, 60),
        (105, 5, 4, 50),
    ]


def test_mgnote_shift_noop_when_all_zero():
    note = M.tap(10, 4, 2)
    before = note.info
    assert note.shift() is note
    assert note.info is before
    assert note.tick == 10


def test_note_ground_with_air_and_air_slide_shifts_all_nodes():
    tap = Tap(tick=100, x=4, width=2).air(AirSlide(height=80).step(200, x=8, width=2, height=100))

    tap.shift(t=5, h=10)

    assert tap.tick == 105
    air = tap._air
    assert isinstance(air, AirSlide)
    assert air.height == 90
    assert air._air_info.height == 90
    assert air.joints[-1].tick == 205
    assert air.joints[-1].height == 110


def test_note_slide_shifts_begin_and_all_joints():
    slide = Slide(tick=100, x=0, width=4).step(150, x=2, width=4).step(200, x=4, width=4)
    slide.shift(t=10, x=1, w=1, h=5)
    assert slide.tick == 110
    assert slide.x == 1
    assert slide.width == 5
    assert slide._info.height == 805
    assert slide.joints[0].tick == 160
    assert slide.joints[0].x == 3
    assert slide.joints[1].tick == 210
    assert slide.joints[1].x == 5


def test_note_hold_and_slide_air_shift():
    hold = Hold(tick=50, x=1, width=3).step(120).air(AirHold(height=70).step(160))
    hold.shift(t=3)

    assert hold.tick == 53
    end = hold.joints[-1]
    assert end.tick == 123
    assert isinstance(hold._air, AirHold)
    assert hold._air.joints[-1].tick == 163

    slide = Slide(tick=10, x=0, width=2).step(30, x=4, width=2).air(AirDirection.DOWN)
    slide.shift(h=20)
    assert slide._info.height == 820
    assert isinstance(slide._air, Air)


def test_note_air_crush_shifts_begin_controls_and_end():
    crush = (
        AirCrush(tick=0, x=1, width=2, height=80, density=5, color=AirCrushColor.RED)
        .control(50, x=2, width=2, height=90)
        .control(100, x=3, width=2, height=70)
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


def test_note_shift_then_to_mg_matches_mg_shift_on_wrapped_tree():
    tap = Tap(tick=100, x=4, width=2).air(AirSlide(height=80).step(200, x=8, width=2, height=100))

    note_path = copy.deepcopy(tap)
    note_path.shift(t=5, x=1, w=0, h=10)
    note_geom = _collect_geometry(note_path.to_mg())

    mg_path = wrap_mg_note(tap.to_mg())
    mg_path.shift(t=5, x=1, w=0, h=10)
    mg_geom = _collect_geometry(mg_path.to_mg())

    assert note_geom == mg_geom


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
    note = M.tap(1, 2, 1, timeline_id=42)
    note._id = 99
    note.shift(t=3)
    assert note._id == 99
    assert note.timeline_id == 42
    assert note.type is NoteType.TAP
