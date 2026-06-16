import pytest

from margrete_rpc import Margrete
from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart.notes import AirSlide, Hold, NoteInfo, R, Slide, Tap
from margrete_rpc.chart.time import (
    Position,
    pop_tick_resolver,
    push_tick_resolver,
    resolve_tick,
)

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
    assert NoteInfo(p=(1, 0, 0)).t == BAR
    # The t setter resolves a position, and copy() (dataclasses.replace) goes through __init__.
    info = NoteInfo()
    info.t = (0, 1, 0)
    assert info.t == BEAT
    assert info.copy(p=(2, 0)).t == 2 * BAR
    # Plain ints pass straight through t, including negatives (RawNote stays permissive).
    info.t = -5
    assert info.t == -5


def test_note_tap_accepts_position_tuple():
    assert Tap(t=(1, 0), x=0, w=4).t == BAR
    assert Tap(t=1920, x=0, w=4).t == 1920  # int still works


def test_note_chained_joints_accept_positions():
    note = Tap(t=(1, 0), x=0, w=4).with_air(
        AirSlide(t=(1, 0), x=0, w=4, h=80)
        .with_ctrl(t=(1, 1), x=5, w=4, h=100)
        .with_step(t=(1, 2), x=5, w=4, h=100)
    )
    assert note.t == BAR
    assert [int(j.t) for j in note._air.joints] == [BAR + BEAT, BAR + 2 * BEAT]


def test_note_slide_and_hold_steps_accept_positions():
    slide = Slide(t=(0, 0), x=0, w=4).with_step(t=(0, 1), x=0, w=4).with_step(t=(0, 2), x=0, w=4)
    assert [int(j.t) for j in slide.joints] == [BEAT, 2 * BEAT]

    hold = Hold(t=(0, 0), x=1, w=3).with_step(t=(1, 0), x=1, w=3)
    assert int(hold.joints[-1].t) == BAR


def test_p_getter_computes_position_from_tick():
    # p is computed from t (4/4 fallback): beat 1 of bar 1, plus a 1/8 offset.
    tap = Tap(t=BAR + BEAT + 240, x=0, w=4)
    assert tap.p == Position(1, 1, 240)
    assert (tap.p.bar, tap.p.beat, tap.p.offset) == (1, 1, 240)
    # the read-only p view round-trips back through the t setter
    tap.t = tap.p
    assert tap.t == BAR + BEAT + 240
    assert NoteInfo(t=BAR).p == (1, 0, 0)
    assert R.tap(t=BEAT, x=0, w=2).p == (0, 1, 0)


def test_raw_factory_accepts_positions_and_t_setter_resolves():
    note = R.tap(t=(2, 0), x=4, w=2)
    assert note.t == 2 * BAR
    note.t = (0, 1, 0)
    assert note.t == BEAT

    seg = R.slide_begin(t=(1, 0), x=0, w=4)
    assert seg.t == BAR


def _begin_with_beat(beats_per_bar, beat_unit):
    return messages_pb2.Envelope(
        begin_edit_response=messages_pb2.BeginEditResponse(
            current_tick=0,
            snapshot=True,
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

    with mg.open_edit() as tx:
        # 3/4 => bar length is 3 * 480 = 1440 ticks
        tap = Tap(t=(1, 0), x=0, w=4)
        assert tap.t == 3 * BEAT
        assert Tap(t=(0, 2), x=0, w=4).t == 2 * BEAT  # beat 2 is valid in 3/4
        # the NoteInfo sink resolves against the same active context
        assert NoteInfo(p=(1, 0)).t == 3 * BEAT
        tx.chart.notes.append(tap)

    # resolver is removed once the transaction exits
    assert resolve_tick((1, 0)) == BAR
