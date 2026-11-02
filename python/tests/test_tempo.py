from fractions import Fraction

import pytest
from margrete_rpc.chart import Chart
from margrete_rpc.chart.diff import build_apply_edit_request, capture_edit_snapshot
from margrete_rpc.chart.events import BeatEvent, BpmEvent
from margrete_rpc.chart.time import pop_tick_resolver, pos_to_tick, push_tick_resolver
from margrete_rpc.chart.util import BpmDivisionResult, BpmPulseResult, bpm_divide, bpm_pulse


def _elapsed(bpms, start, end):
    """Integrate the installed tempo map independently of the returned result."""
    ordered = sorted({event.t: event for event in bpms}.values(), key=lambda event: event.t)
    bpm = next(event.bpm for event in reversed(ordered) if event.t <= start)
    duration = Fraction()
    cursor = start
    for event in ordered:
        if start < event.t < end:
            duration += Fraction(60_000 * (event.t - cursor), 480) / Fraction(bpm)
            cursor, bpm = event.t, event.bpm
    return duration + Fraction(60_000 * (end - cursor), 480) / Fraction(bpm)


def _assert_atomic_failure(chart, function, kwargs, error=ValueError, match=None):
    original = chart.bpms
    state = [(id(event), repr(event)) for event in original]
    with pytest.raises(error, match=match):
        function(chart.bpms, **kwargs)
    assert chart.bpms is original
    assert [(id(event), repr(event)) for event in chart.bpms] == state


@pytest.fixture(params=["pulse", "divide"])
def adjustment_factory(request):
    if request.param == "pulse":
        return lambda bpms: bpm_pulse(bpms, t=100, length=5, span=240, bpm_scale=100)
    return lambda bpms: bpm_divide(bpms, t=100, span=240, count=5, step=30)


@pytest.mark.parametrize("source_type", [list, tuple, iter])
def test_standalone_generation_and_application(adjustment_factory, source_type):
    bpms = [BpmEvent(400, 300), BpmEvent(0, 193), BpmEvent(340, 240)]
    original = bpms.copy()
    state = [(id(event), repr(event)) for event in bpms]
    result = adjustment_factory(source_type(bpms))
    assert [(id(event), repr(event)) for event in bpms] == state
    assert (result.start, result.end) == (100, 340)
    result.apply(bpms)
    assert bpms[0] is original[1]
    assert bpms[-2] is original[2]
    assert bpms[-1] is original[0]
    assert abs(_elapsed(bpms, 100, 340) - _elapsed(original, 100, 340)) < Fraction(1, 10**12)


def test_generation_leaves_chart_and_edit_diff_untouched(adjustment_factory):
    chart = Chart(bpms=[BpmEvent(400, 300), BpmEvent(0, 193), BpmEvent(340, 240)])
    original_list = chart.bpms
    state = [(id(event), repr(event)) for event in chart.bpms]
    snapshot = capture_edit_snapshot(chart)
    result = adjustment_factory(chart.bpms)
    assert result.events[-1] == BpmEvent(340, 193)
    assert chart.bpms is original_list
    assert [(id(event), repr(event)) for event in chart.bpms] == state
    assert (
        build_apply_edit_request(
            chart,
            snapshot_enabled=True,
            replace_all_notes=False,
            replace_all_events=False,
            snapshot=snapshot,
        )
        is None
    )


def test_duplicate_events_follow_chart_last_value_rule(adjustment_factory):
    at_end = BpmEvent(340, 240)
    chart = Chart(
        bpms=[
            BpmEvent(0, float("nan")),
            BpmEvent(0, 193),
            BpmEvent(110, 120),
            BpmEvent(110, 193),
            BpmEvent(340, 120),
            at_end,
            BpmEvent(400, 120),
            BpmEvent(400, 300),
        ]
    )
    expected = _elapsed(chart.bpms, 100, 340)
    result = adjustment_factory(chart.bpms)
    result.apply(chart.bpms)
    assert len({event.t for event in chart.bpms}) == len(chart.bpms)
    assert next(event for event in chart.bpms if event.t == 340) is at_end
    assert chart.bpms[-1] == BpmEvent(400, 300)
    assert abs(_elapsed(chart.bpms, 100, 340) - expected) < Fraction(1, 10**12)


def test_apply_preserves_current_endpoint_and_copies_generated_events(adjustment_factory):
    source = Chart(bpms=[BpmEvent(0, 193)])
    result = adjustment_factory(source.bpms)
    boundary = BpmEvent(340, 240)
    target = Chart(bpms=[BpmEvent(0, 193), BpmEvent(150, 193), boundary])
    result.apply(target.bpms)
    assert source.bpms == [BpmEvent(0, 193)]
    assert target.bpms[-1] is boundary
    assert all(event.t != 150 for event in target.bpms)
    applied_first = next(event for event in target.bpms if event.t == 100)
    assert applied_first == result.events[0]
    assert applied_first is not result.events[0]
    result.events[0].bpm = 999
    assert applied_first.bpm != 999


@pytest.mark.parametrize(
    "replacement,match",
    [
        ([BpmEvent(0, 240)], "original BPM"),
        ([BpmEvent(0, 193), BpmEvent(120, 240)], "conflicts"),
        ([], "no effective BPM"),
    ],
)
def test_apply_rechecks_source_before_any_write(adjustment_factory, replacement, match):
    chart = Chart(bpms=[BpmEvent(0, 193)])
    result = adjustment_factory(chart.bpms)
    chart.bpms[:] = replacement
    _assert_atomic_failure(chart, result.apply, {}, match=match)


@pytest.mark.parametrize("change", ["bpm", "start", "order", "end"])
def test_apply_rejects_invalid_generated_events_atomically(adjustment_factory, change):
    chart = Chart(bpms=[BpmEvent(0, 193)])
    result = adjustment_factory(chart.bpms)
    if change == "bpm":
        result.events[0].bpm = float("nan")
    elif change == "start":
        result.events[0].t += 1
    elif change == "order":
        result.events[1].t = result.events[0].t
    else:
        result.events[-1].t -= 1
    _assert_atomic_failure(chart, result.apply, {})


def test_pulse_tutorial_values():
    chart = Chart(bpms=[BpmEvent(0, 240)])
    result = bpm_pulse(chart.bpms, t=0, length=(1, 384), span=(1, 48), bpm_scale=100)
    assert [event.bpm for event in result.events] == pytest.approx([24000, 210.2628285356696, 240])
    result.apply(chart.bpms)
    assert float(_elapsed(chart.bpms, result.start, result.pivot)) == pytest.approx(0.0260416666667)
    assert abs(_elapsed(chart.bpms, result.start, result.end) - Fraction(125, 6)) < Fraction(
        1, 10**12
    )


@pytest.mark.parametrize("length,span,factor", [((1, 384), (1, 48), 1), (10, 80, 2)])
def test_pulse_reference_values(length, span, factor):
    chart = Chart(bpms=[BpmEvent(0, 240)])
    result = bpm_pulse(chart.bpms, t=(130, 0, 120), length=length, span=span, bpm_scale=22)
    start = 130 * 1920 + 120
    assert isinstance(result, BpmPulseResult)
    assert (result.start, result.pivot, result.end) == (
        start,
        start + 5 * factor,
        start + 40 * factor,
    )
    assert [(e.t - start, e.bpm) for e in result.events] == [
        (0, 5280),
        (5 * factor, 211.2),
        (40 * factor, 240),
    ]
    assert chart.bpms == [BpmEvent(0, 240)]
    result.apply(chart.bpms)
    assert float(_elapsed(chart.bpms, start, result.pivot)) == pytest.approx(
        0.118371212121 * factor, abs=1e-12
    )
    assert float(_elapsed(chart.bpms, start, result.end)) == pytest.approx(
        20.833333333333 * factor, abs=1e-12
    )


@pytest.mark.parametrize(
    "kwargs", [{"bpm_scale": Fraction(1, 2)}, {"duration_ms": Fraction(125, 24)}]
)
def test_pulse_stretch_by_scale_or_milliseconds(kwargs):
    chart = Chart(bpms=[BpmEvent(0, 240)])
    result = bpm_pulse(chart.bpms, t=0, length=5, span=40, **kwargs)
    assert [e.bpm for e in result.events] == [120, 280, 240]
    result.apply(chart.bpms)
    assert _elapsed(chart.bpms, result.start, result.pivot) == Fraction(125, 24)
    assert _elapsed(chart.bpms, result.start, result.end) == Fraction(125, 6)


def test_pulse_requested_milliseconds_preserves_total_time():
    chart = Chart(bpms=[BpmEvent(0, 193)])
    requested = Fraction(1, 7)
    result = bpm_pulse(chart.bpms, t=0, length=5, span=40, duration_ms=requested)
    result.apply(chart.bpms)
    actual = _elapsed(chart.bpms, 0, 5)
    actual_span = _elapsed(chart.bpms, 0, 40)
    assert abs(actual - requested) < Fraction(1, 10**12)
    assert abs(actual_span - Fraction(60_000 * 40, 480 * 193)) < Fraction(1, 10**12)


@pytest.mark.parametrize("count,first_bpm,last_bpm", [(5, 120.625, 482.5), (7, 168.875, 337.75)])
def test_division_reference_values(count, first_bpm, last_bpm):
    chart = Chart(bpms=[BpmEvent(0, 193)])
    result = bpm_divide(chart.bpms, t=(24, 2), span=(1, 8), count=count, step=(1, 64))
    start = 24 * 1920 + 960
    assert isinstance(result, BpmDivisionResult)
    assert result.start == start
    assert result.ticks == tuple(start + 30 * i for i in range(count))
    assert result.end == start + 240
    assert result.end not in result.ticks
    assert [(e.t - start, e.bpm) for e in result.events] == [
        (0, first_bpm),
        (30 * (count - 1), last_bpm),
        (240, 193),
    ]
    expected = Fraction(60_000 * 240, 480 * 193 * count)
    result.apply(chart.bpms)
    for a, b in zip(result.ticks, (*result.ticks[1:], result.end)):
        assert _elapsed(chart.bpms, a, b) == expected


@pytest.mark.parametrize(
    "count,offsets",
    [
        (5, (0, 50, 95, 145, 190)),
        (7, (0, 35, 70, 105, 135, 170, 205)),
        (9, (0, 25, 55, 80, 105, 135, 160, 185, 215)),
    ],
)
def test_division_automatic_grid_keeps_equal_elapsed_intervals(count, offsets):
    chart = Chart(bpms=[BpmEvent(0, 193)])
    result = bpm_divide(chart.bpms, t=100, span=240, count=count)
    assert result.ticks == tuple(100 + offset for offset in offsets)
    assert all(e.t % 5 == 0 for e in result.events)
    result.apply(chart.bpms)
    actual = tuple(
        _elapsed(chart.bpms, a, b) for a, b in zip(result.ticks, (*result.ticks[1:], result.end))
    )
    target = Fraction(60_000 * 240, 480 * 193 * count)
    assert max(abs(d - target) for d in actual) < Fraction(1, 10**12)
    assert abs(sum(actual) - count * target) < Fraction(1, 10**12)


def test_division_rounding_ties_go_forward_and_native_grid_accepts_single_ticks():
    chart = Chart(bpms=[BpmEvent(0, 120)])
    result = bpm_divide(chart.bpms, t=0, span=15, count=2)
    assert result.ticks == (0, 10)
    result.apply(chart.bpms)
    result = bpm_divide(chart.bpms, t=16, span=(3, 1920), count=3, grid=1)
    assert result.ticks == (16, 17, 18)
    assert result.end == 19
    result.apply(chart.bpms)
    pulse = bpm_pulse(chart.bpms, t=19, length=(1, 1920), span=3, bpm_scale=2, grid=1)
    assert [e.t for e in pulse.events] == [19, 20, 22]


@pytest.mark.parametrize("count", [1, 8])
def test_division_uniform_intervals_coalesce_but_keep_restoration(count):
    chart = Chart(bpms=[BpmEvent(0, 193)])
    result = bpm_divide(chart.bpms, t=0, span=240, count=count)
    assert len(result.ticks) == count
    assert result.events == (BpmEvent(0, 193), BpmEvent(240, 193))


def test_positions_use_active_resolver_like_other_tools():
    bpms = [BpmEvent(0, 120)]
    beats = [BeatEvent(0, 3, 4), BeatEvent(2, 7, 8)]
    token = push_tick_resolver(lambda pos: pos_to_tick(*pos, beat_events=beats))
    try:
        result = bpm_pulse(bpms, t=(2, 6, 5), length=5, span=40, bpm_scale=2)
        assert result.start == 2 * 1440 + 6 * 240 + 5
        division = bpm_divide(bpms, t=(3,), span=240, count=5)
        assert division.ticks[0] == 2 * 1440 + 7 * 240
        beats[1].beats_per_bar = 5
        assert bpm_divide(bpms, t=(3,), span=240, count=5).start == 2 * 1440 + 5 * 240
    finally:
        pop_tick_resolver(token)
    assert bpm_pulse(bpms, t=(3,), length=5, span=40, bpm_scale=2).start == 3 * 1920
    assert bpm_divide(bpms, t=(3,), span=240, count=5).start == 3 * 1920


def test_explicit_ticks_support_offline_time_signatures_and_bypass_resolver():
    bpms = [BpmEvent(0, 120)]
    beats = [BeatEvent(0, 3, 4), BeatEvent(2, 7, 8)]
    start = pos_to_tick(3, beat_events=beats)
    pulse = bpm_pulse(bpms, t=start, length=5, span=40, bpm_scale=2)
    division = bpm_divide(bpms, t=start, span=240, count=5)
    assert pulse.start == division.start == 2 * 1440 + 7 * 240
    token = push_tick_resolver(lambda pos: pytest.fail("explicit ticks must bypass the resolver"))
    try:
        assert bpm_pulse(bpms, t=start, length=5, span=40, bpm_scale=2) == pulse
        assert bpm_divide(bpms, t=start, span=240, count=5) == division
    finally:
        pop_tick_resolver(token)


@pytest.mark.parametrize("kind", ["pulse", "division"])
def test_boundaries_and_redundant_source_events_and_diff(kind):
    before, at_start, redundant, at_end, after = (
        BpmEvent(0, 120),
        BpmEvent(100, 193),
        BpmEvent(110, 193),
        BpmEvent(340, 240),
        BpmEvent(400, 300),
    )
    chart = Chart(bpms=[after, redundant, before, at_end, at_start])
    original_list = chart.bpms
    snapshot = capture_edit_snapshot(chart)
    if kind == "pulse":
        result = bpm_pulse(chart.bpms, t=100, length=5, span=240, bpm_scale=22)
    else:
        result = bpm_divide(chart.bpms, t=100, span=240, count=5, step=30)
    assert result.events[-1] == BpmEvent(340, 193)
    result.apply(chart.bpms)
    assert chart.bpms is original_list
    assert chart.bpms[0] is before
    assert chart.bpms[-1] is after
    assert chart.bpms[-2] is at_end
    assert redundant not in chart.bpms
    assert at_start.bpm == 193
    assert float(_elapsed(chart.bpms, 100, 340)) == pytest.approx(
        60_000 * 240 / (480 * 193), abs=1e-12
    )
    request = build_apply_edit_request(
        chart,
        snapshot_enabled=True,
        replace_all_notes=False,
        replace_all_events=False,
        snapshot=snapshot,
    )
    assert request is not None
    assert list(request.bpm_ticks_delete) == [110]
    assert [(e.tick, e.bpm) for e in request.bpm_upsert] == [
        (e.t, e.bpm) for e in result.events[:-1]
    ]


@pytest.mark.parametrize("precomputed", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("boundary_bpm", [None, 193])
def test_adjacent_spans_in_either_order_preserve_tempo_and_total_time(
    precomputed, reverse, boundary_bpm
):
    chart = Chart(bpms=[BpmEvent(0, 240)])
    if boundary_bpm is not None:
        chart.bpms.append(BpmEvent(40, boundary_bpm))
    original_duration = _elapsed(chart.bpms, 0, 280)
    operations = [
        lambda: bpm_pulse(chart.bpms, t=0, length=5, span=40, bpm_scale=22),
        lambda: bpm_divide(chart.bpms, t=40, span=240, count=7, step=30),
    ]
    if precomputed:
        results = [operation() for operation in operations]
        for result in reversed(results) if reverse else results:
            result.apply(chart.bpms)
    else:
        for operation in reversed(operations) if reverse else operations:
            operation().apply(chart.bpms)
    assert len({e.t for e in chart.bpms}) == len(chart.bpms)
    assert chart.bpms[-1] == BpmEvent(280, boundary_bpm or 240)
    assert float(_elapsed(chart.bpms, 0, 280)) == pytest.approx(float(original_duration), abs=1e-12)
    assert float(_elapsed(chart.bpms, 40, 70)) == pytest.approx(
        60_000 * 240 / (480 * (boundary_bpm or 240) * 7)
    )


@pytest.mark.parametrize(
    "changes,error,match",
    [
        ({"bpm_scale": None}, ValueError, "exactly one"),
        ({"duration_ms": 1}, ValueError, "exactly one"),
        ({"length": 0}, ValueError, "positive"),
        ({"length": 40}, ValueError, "less than span"),
        ({"length": 45}, ValueError, "less than span"),
        ({"length": (1, 2048)}, ValueError, "exact multiple"),
        ({"span": (1, 7)}, ValueError, "exact multiple"),
        ({"length": (1, 0)}, ValueError, "denominator"),
        ({"length": (1, 2, 3)}, ValueError, "numerator, denominator"),
        ({"span": 41}, ValueError, "exact multiple"),
        ({"t": 1}, ValueError, "absolute multiple"),
        ({"t": -5}, ValueError, "tick"),
        ({"t": 2**31 - 5}, ValueError, "tick"),
        ({"t": ()}, ValueError, "tuple"),
        ({"grid": 0}, ValueError, "grid"),
        ({"grid": 1.5}, TypeError, "int"),
        ({"length": True}, TypeError, "int"),
        ({"length": 5.0}, TypeError, "int"),
        ({"bpm_scale": 0}, ValueError, "positive"),
        ({"bpm_scale": -1}, ValueError, "positive"),
        ({"bpm_scale": float("nan")}, ValueError, "finite"),
        ({"bpm_scale": float("inf")}, ValueError, "finite"),
        ({"bpm_scale": True}, TypeError, "Fraction"),
        ({"bpm_scale": Fraction(1, 8)}, ValueError, "original total duration"),
        ({"bpm_scale": Fraction(1, 9)}, ValueError, "original total duration"),
        (
            {"bpm_scale": None, "duration_ms": Fraction(125, 6)},
            ValueError,
            "original total duration",
        ),
        ({"bpm_scale": None, "duration_ms": 21}, ValueError, "original total duration"),
        ({"bpm_scale": None, "duration_ms": -1}, ValueError, "positive"),
        ({"bpm_scale": None, "duration_ms": float("nan")}, ValueError, "finite"),
        ({"bpm_scale": 1e308}, ValueError, "finite positive float"),
        # The first BPM is representable; the compensation overflows only afterwards.
        (
            {"bpm_scale": None, "duration_ms": Fraction(125, 6) - Fraction(1, 10**310)},
            ValueError,
            "finite positive float",
        ),
    ],
)
def test_invalid_pulse_is_atomic(changes, error, match):
    chart = Chart(bpms=[BpmEvent(0, 240)])
    kwargs = dict(t=0, length=5, span=40, bpm_scale=22)
    kwargs.update(changes)
    _assert_atomic_failure(chart, bpm_pulse, kwargs, error, match)


@pytest.mark.parametrize(
    "changes,error,match",
    [
        ({"count": 0}, ValueError, "positive"),
        ({"count": -1}, ValueError, "positive"),
        ({"count": True}, TypeError, "int"),
        ({"count": 5.0}, TypeError, "int"),
        ({"count": 49}, ValueError, "too short"),
        ({"span": (1, 7)}, ValueError, "exact multiple"),
        ({"step": (1, 7)}, ValueError, "exact multiple"),
        ({"step": 0}, ValueError, "positive"),
        ({"step": -5}, ValueError, "positive"),
        ({"step": 60}, ValueError, "positive final interval"),
        ({"step": 65}, ValueError, "positive final interval"),
    ],
)
def test_invalid_division_is_atomic(changes, error, match):
    chart = Chart(bpms=[BpmEvent(0, 193)])
    kwargs = dict(t=0, span=240, count=5)
    kwargs.update(changes)
    _assert_atomic_failure(chart, bpm_divide, kwargs, error, match)


@pytest.mark.parametrize(
    "function,kwargs",
    [
        (bpm_pulse, dict(t=0, length=5, span=40, bpm_scale=22)),
        (bpm_divide, dict(t=0, span=40, count=5)),
    ],
)
@pytest.mark.parametrize(
    "bpms,match",
    [
        ([], "no effective BPM"),
        ([BpmEvent(5, 240)], "no effective BPM"),
        ([BpmEvent(0, 240), BpmEvent(5, 193)], "conflicts"),
        ([BpmEvent(0, 240), BpmEvent(10, 193), BpmEvent(15, 240)], "conflicts"),
        ([BpmEvent(0, 240), BpmEvent(40, 0)], "positive"),
        ([BpmEvent(0, -1)], "positive"),
        ([BpmEvent(0, float("nan"))], "finite"),
        ([BpmEvent(0, float("inf"))], "finite"),
        ([BpmEvent(-5, 240)], "tick"),
    ],
)
def test_invalid_source_or_conflict_is_atomic(function, kwargs, bpms, match):
    _assert_atomic_failure(Chart(bpms=bpms), function, kwargs, match=match)


@pytest.mark.parametrize("bpm,step", [(1e308, 5), (5e-324, 5)])
def test_unrepresentable_division_output_is_atomic(bpm, step):
    _assert_atomic_failure(
        Chart(bpms=[BpmEvent(0, bpm)]),
        bpm_divide,
        dict(t=0, span=240, count=5, step=step),
        match="float",
    )
