import pytest

from margrete_rpc import AirSlide, Hold, M, Margrete, NoteInfo, Slide, Tap
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart.time import pop_tick_resolver, push_tick_resolver, resolve_tick

BEAT = 480
BAR = 1920


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, envelope):
        self.requests.append(envelope)
        return self.responses.pop(0)


def test_resolve_tick_passes_int_through():
    assert resolve_tick(7) == 7
    assert resolve_tick(-3) == -3


def test_resolve_tick_4_4_fallback_without_context():
    assert resolve_tick((1, 0, 0)) == BAR
    assert resolve_tick((0, 1)) == BEAT
    assert resolve_tick((0,)) == 0


def test_resolve_tick_rejects_wrong_tuple_length():
    with pytest.raises(ValueError):
        resolve_tick((1, 2, 3, 4))


def test_resolve_tick_uses_active_resolver():
    token = push_tick_resolver(lambda pos: 100 + sum(pos))
    try:
        assert resolve_tick((1, 2)) == 103
    finally:
        pop_tick_resolver(token)
    # restored to the 4/4 fallback afterwards
    assert resolve_tick((1, 0)) == BAR


def test_noteinfo_is_the_resolution_sink():
    # Construction resolves a tuple position to a tick (4/4 fallback).
    assert NoteInfo(t=(1, 0, 0)).t == BAR
    # Later assignment resolves too, and copy() (dataclasses.replace) goes through __init__.
    info = NoteInfo()
    info.t = (0, 1)
    assert info.t == BEAT
    assert info.copy(t=(2, 0)).t == 2 * BAR
    # Plain ints pass straight through, including negatives (MgNote stays permissive).
    info.t = -5
    assert info.t == -5


def test_note_tap_accepts_position_tuple():
    assert Tap((1, 0), 0, 4).t == BAR
    assert Tap(1920, 0, 4).t == 1920  # int still works


def test_note_chained_joints_accept_positions():
    note = Tap((1, 0), 0, 4).air(AirSlide(h=80).control((1, 1), x=5, h=100).step((1, 2), h=100))
    assert note.t == BAR
    assert [int(j.t) for j in note._air.joints] == [BAR + BEAT, BAR + 2 * BEAT]


def test_note_slide_and_hold_steps_accept_positions():
    slide = Slide((0, 0), 0, 4).step((0, 1)).step((0, 2))
    assert [int(j.t) for j in slide.joints] == [BEAT, 2 * BEAT]

    hold = Hold((0, 0), 1, 3).step((1, 0))
    assert int(hold.joints[-1].t) == BAR


def test_mg_factory_and_setter_accept_positions():
    note = M.tap((2, 0), 4, 2)
    assert note.t == 2 * BAR
    note.t = (0, 1, 0)
    assert note.t == BEAT

    seg = M.slide_begin((1, 0), 0, 4)
    assert seg.t == BAR


def _begin_with_beat(beats_per_bar, beat_unit):
    return messages_pb2.Envelope(
        begin_edit_response=messages_pb2.BeginEditResponse(
            current_tick=0,
            scan=True,
            beat_change_events=[
                messages_pb2.BeatChangeEvent(
                    bar=0, beats_per_bar=beats_per_bar, beat_unit=beat_unit
                )
            ],
        )
    )


def test_open_edit_resolves_positions_against_chart_time_signature():
    transport = FakeTransport(
        [
            _begin_with_beat(3, 4),
            messages_pb2.Envelope(apply_edit_response=messages_pb2.ApplyEditResponse()),
        ]
    )
    mg = Margrete(transport=transport)

    with mg.open_edit("pos") as tx:
        # 3/4 => bar length is 3 * 480 = 1440 ticks
        tap = Tap((1, 0), 0, 4)
        assert tap.t == 3 * BEAT
        assert Tap((0, 2), 0, 4).t == 2 * BEAT  # beat 2 is valid in 3/4
        # the NoteInfo sink resolves against the same active context
        assert NoteInfo(t=(1, 0)).t == 3 * BEAT
        tx.chart.notes.append(tap)

    # resolver is removed once the transaction exits
    assert resolve_tick((1, 0)) == BAR
