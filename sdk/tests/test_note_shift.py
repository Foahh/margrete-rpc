from margrete_rpc import L, LLNote


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


from margrete_rpc import AirDirection, Tap


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
