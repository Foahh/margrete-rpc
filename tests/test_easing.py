import math

import pytest

from margrete_rpc.chart.util import EASINGS, Easing, resolve_easing
from margrete_rpc.chart.util.easing import EaseName

ALL = sorted(EASINGS)
IN_OUT = [name for name in ALL if name.startswith("in_out_")]


@pytest.mark.parametrize("name", ALL)
def test_endpoints(name: str) -> None:
    ease = EASINGS[name]
    assert ease.solve(0.0) == pytest.approx(0.0, abs=1e-9)
    assert ease.solve(1.0) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("name", ALL)
def test_monotonic(name: str) -> None:
    ease = EASINGS[name]
    values = [ease.solve(i / 200) for i in range(201)]
    for prev, cur in zip(values, values[1:]):
        assert cur >= prev - 1e-9


@pytest.mark.parametrize("name", ALL)
def test_inverse_round_trip(name: str) -> None:
    ease = EASINGS[name]
    for i in range(1, 200):
        t = i / 200
        assert ease.inverse(ease.solve(t)) == pytest.approx(t, abs=1e-6)
        y = i / 200
        assert ease.solve(ease.inverse(y)) == pytest.approx(y, abs=1e-6)


@pytest.mark.parametrize("name", IN_OUT)
def test_in_out_symmetry(name: str) -> None:
    assert EASINGS[name].solve(0.5) == pytest.approx(0.5, abs=1e-9)


def test_easename_matches_registry() -> None:
    assert set(EaseName.__args__) == set(EASINGS)


def test_resolve_easing_name() -> None:
    assert resolve_easing("in_out_sine") is EASINGS["in_out_sine"]


def test_resolve_easing_passthrough() -> None:
    ease = EASINGS["linear"]
    assert resolve_easing(ease) is ease


def test_resolve_easing_unknown_name() -> None:
    with pytest.raises(ValueError):
        resolve_easing("wobble")


def test_resolve_easing_callable_numeric_inverse() -> None:
    ease = resolve_easing(lambda t: t * t)
    assert ease._inverse is None
    assert ease.solve(0.5) == pytest.approx(0.25)
    # numeric (bisection) inverse still recovers progress
    assert ease.inverse(0.25) == pytest.approx(0.5, abs=1e-6)


def test_resolve_easing_bad_type() -> None:
    with pytest.raises(TypeError):
        resolve_easing(123)  # type: ignore[arg-type]


def test_known_analytic_values() -> None:
    assert EASINGS["in_out_sine"].solve(0.5) == pytest.approx(0.5)
    assert EASINGS["in_quad"].solve(0.5) == pytest.approx(0.25)
    assert EASINGS["out_quad"].solve(0.5) == pytest.approx(0.75)
    assert EASINGS["in_sine"].solve(1.0) == pytest.approx(1.0)
    assert EASINGS["in_out_circ"].inverse(0.5) == pytest.approx(0.5)


def test_custom_easing_bisection_matches_analytic() -> None:
    custom = Easing("cube", lambda t: t**3)
    for i in range(1, 100):
        y = i / 100
        assert custom.inverse(y) == pytest.approx(y ** (1 / 3), abs=1e-5)
        assert custom.solve(custom.inverse(y)) == pytest.approx(y, abs=1e-6)
    assert math.isclose(custom.solve(0.5), 0.125)
