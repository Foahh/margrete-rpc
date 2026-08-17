import pytest
from margrete_rpc.chart.events import TimelineSpeedEvent
from margrete_rpc.chart.time import pos_to_tick
from margrete_rpc.chart.util import timing_easing, timing_easing_by_disp, timing_glitch
from margrete_rpc.chart.util.easing import resolve_easing


def test_glitch_event_count_and_spike_pattern() -> None:
    events = timing_glitch(t0=0, t1=1920, count=4, speed_range=2.0, base_speed=1.0, til=3)
    assert all(isinstance(e, TimelineSpeedEvent) for e in events)
    assert all(e.til == 3 for e in events)
    assert len(events) == 2 * 4

    spikes = events[0::2]
    resets = events[1::2]
    assert [s.speed for s in spikes] == [-1.0, 3.0, -1.0, 3.0]
    assert all(r.speed == 1.0 for r in resets)
    for spike, reset in zip(spikes, resets):
        assert reset.t == spike.t + 5
    assert all(0 <= e.t < 1920 for e in spikes)


def test_glitch_spike_ticks_controls_reset_offset() -> None:
    events = timing_glitch(t0=0, t1=1920, count=4, speed_range=2.0, base_speed=1.0, spike_ticks=3)
    spikes = events[0::2]
    resets = events[1::2]
    for spike, reset in zip(spikes, resets):
        assert reset.t == spike.t + 3


def test_glitch_invalid_spike_ticks_raises() -> None:
    with pytest.raises(ValueError):
        timing_glitch(t0=0, t1=1920, count=4, speed_range=2.0, base_speed=1.0, spike_ticks=0)


def test_easing_endpoints_and_linear_ramp() -> None:
    events = timing_easing(
        t0=0, t1=1920, start_speed=1.0, end_speed=2.0, count=8, easing="linear", til=2
    )
    assert all(isinstance(e, TimelineSpeedEvent) for e in events)
    assert all(e.til == 2 for e in events)
    assert len(events) == 9
    assert events[0].t == 0
    assert events[-1].t == 1920
    assert events[0].speed == pytest.approx(1.0)
    assert events[-1].speed == pytest.approx(2.0)

    speeds = [e.speed for e in events]
    for prev, cur in zip(speeds, speeds[1:]):
        assert cur >= prev
    # linear easing is an evenly-spaced ramp
    assert events[4].speed == pytest.approx(1.5)


def test_easing_monotonic_for_monotonic_easing() -> None:
    events = timing_easing(
        t0=0, t1=3840, start_speed=0.5, end_speed=3.0, count=16, easing="in_out_sine"
    )
    speeds = [e.speed for e in events]
    assert speeds[0] == pytest.approx(0.5)
    assert speeds[-1] == pytest.approx(3.0)
    for prev, cur in zip(speeds, speeds[1:]):
        assert cur >= prev - 1e-9


def test_easing_by_disp_linear_is_constant_velocity() -> None:
    events = timing_easing_by_disp(t0=0, t1=1920, base_speed=2.0, count=8, easing="linear", til=1)
    assert all(isinstance(e, TimelineSpeedEvent) for e in events)
    assert all(e.til == 1 for e in events)
    assert len(events) == 9
    assert all(e.speed == pytest.approx(2.0) for e in events)


def test_easing_by_disp_steeper_curve_accelerates() -> None:
    events = timing_easing_by_disp(t0=0, t1=1920, base_speed=2.0, count=8, easing="in_quad")
    # in_quad accelerates: slope near the end exceeds slope near the start
    assert events[-1].speed > events[0].speed


def test_easing_by_disp_displacement_lands_on_easing_curve() -> None:
    base_speed = 1.5
    span = 1920
    count = 12
    ease = resolve_easing("out_cubic")
    events = timing_easing_by_disp(
        t0=0, t1=span, base_speed=base_speed, count=count, easing="out_cubic"
    )
    disp = 0.0
    for i in range(count):
        assert disp == pytest.approx(base_speed * span * ease.solve(i / count))
        disp += events[i].speed * (events[i + 1].t - events[i].t)
    assert disp == pytest.approx(base_speed * span * ease.solve(1.0))


@pytest.mark.parametrize(
    "func",
    [
        lambda **kw: timing_glitch(speed_range=1.0, base_speed=0.0, **kw),
        lambda **kw: timing_easing(start_speed=1.0, end_speed=2.0, **kw),
        lambda **kw: timing_easing_by_disp(base_speed=1.0, easing="linear", **kw),
    ],
)
def test_invalid_count_and_range_raise(func) -> None:
    with pytest.raises(ValueError):
        func(t0=0, t1=1920, count=0)
    with pytest.raises(ValueError):
        func(t0=1920, t1=1920, count=4)


def test_accepts_position_like() -> None:
    # Outside a transaction, positions resolve with a default 4/4 signature.
    events = timing_easing(t0=(0, 0, 0), t1=(2, 0, 0), start_speed=1.0, end_speed=2.0, count=4)
    assert events[0].t == pos_to_tick(0, 0, 0, beat_events=())
    assert events[-1].t == pos_to_tick(2, 0, 0, beat_events=())
