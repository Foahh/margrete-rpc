from margrete_rpc import (
    AirCrush,
    AirCrushColor,
    AirDirection,
    Hold,
    L,
    LLNote,
    Slide,
    Tap,
)


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
    slide = (
        Slide(tick=100, x=0, width=4, height=80)
        .step(150, x=2, width=4)
        .end(200, x=4, width=4)
    )
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
