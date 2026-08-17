from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

type EaseLike = str | Easing | Callable[[float], float]
"""An input easing: a registry name, an :class:`Easing`, or a bare ``[0,1]->[0,1]`` callable.

Resolve via :func:`resolve_easing`."""

EaseName = Literal[
    "linear",
    "in_sine",
    "out_sine",
    "in_out_sine",
    "in_quad",
    "out_quad",
    "in_out_quad",
    "in_cubic",
    "out_cubic",
    "in_out_cubic",
    "in_quart",
    "out_quart",
    "in_out_quart",
    "in_quint",
    "out_quint",
    "in_out_quint",
    "in_expo",
    "out_expo",
    "in_out_expo",
    "in_circ",
    "out_circ",
    "in_out_circ",
]
"""The names of the built-in easings in :data:`EASINGS` (for editor autocomplete)."""


@dataclass(frozen=True, slots=True)
class Easing:
    """A ``[0,1] -> [0,1]`` easing curve with a forward ``solve``.

    ``solve`` may be any shape, including non-monotonic curves that overshoot or oscillate
    (bounce, back, elastic, custom beziers). It should satisfy ``solve(0) == 0`` and
    ``solve(1) == 1`` so a leg lands exactly on its waypoints.
    """

    name: str
    solve: Callable[[float], float]


def _power(n: int) -> tuple[Easing, Easing, Easing]:
    def in_(t: float) -> float:
        return t**n

    def out(t: float) -> float:
        return 1.0 - (1.0 - t) ** n

    def in_out(t: float) -> float:
        if t < 0.5:
            return (2.0 * t) ** n / 2.0
        return 1.0 - (2.0 - 2.0 * t) ** n / 2.0

    family = {2: "quad", 3: "cubic", 4: "quart", 5: "quint"}[n]
    return (
        Easing(f"in_{family}", in_),
        Easing(f"out_{family}", out),
        Easing(f"in_out_{family}", in_out),
    )


def _sine() -> tuple[Easing, Easing, Easing]:
    half_pi = math.pi / 2.0

    return (
        Easing("in_sine", lambda t: 1.0 - math.cos(t * half_pi)),
        Easing("out_sine", lambda t: math.sin(t * half_pi)),
        Easing("in_out_sine", lambda t: (1.0 - math.cos(math.pi * t)) / 2.0),
    )


def _circ() -> tuple[Easing, Easing, Easing]:
    def in_(t: float) -> float:
        return 1.0 - math.sqrt(1.0 - t * t)

    def out(t: float) -> float:
        return math.sqrt(1.0 - (1.0 - t) ** 2)

    def in_out(t: float) -> float:
        if t < 0.5:
            return (1.0 - math.sqrt(1.0 - (2.0 * t) ** 2)) / 2.0
        return (math.sqrt(1.0 - (2.0 - 2.0 * t) ** 2) + 1.0) / 2.0

    return (
        Easing("in_circ", in_),
        Easing("out_circ", out),
        Easing("in_out_circ", in_out),
    )


def _expo() -> tuple[Easing, Easing, Easing]:
    def in_(t: float) -> float:
        return 0.0 if t <= 0.0 else 2.0 ** (10.0 * t - 10.0)

    def out(t: float) -> float:
        return 1.0 if t >= 1.0 else 1.0 - 2.0 ** (-10.0 * t)

    def in_out(t: float) -> float:
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        if t < 0.5:
            return 2.0 ** (20.0 * t - 10.0) / 2.0
        return (2.0 - 2.0 ** (-20.0 * t + 10.0)) / 2.0

    return (
        Easing("in_expo", in_),
        Easing("out_expo", out),
        Easing("in_out_expo", in_out),
    )


def _build_registry() -> dict[str, Easing]:
    registry: dict[str, Easing] = {"linear": Easing("linear", lambda t: t)}
    for easing in (*_sine(), *_power(2), *_power(3), *_power(4), *_power(5), *_expo(), *_circ()):
        registry[easing.name] = easing
    return registry


EASINGS: dict[str, Easing] = _build_registry()
"""Built-in easings keyed by name (see :data:`EaseName`).

Includes ``linear`` and the ``in_`` / ``out_`` / ``in_out_`` variants of ``sine``, ``quad``,
``cubic``, ``quart``, ``quint``, ``expo``, and ``circ``."""


def resolve_easing(value: EaseLike) -> Easing:
    """Resolve an :data:`EaseLike` to an :class:`Easing`.

    Args:
        value: A name (see :data:`EaseName`), an :class:`Easing` (returned as-is),
            or a ``[0,1]->[0,1]`` callable.

    Returns:
        The resolved :class:`Easing`.

    Raises:
        ValueError: If ``value`` is an unrecognised easing name.
        TypeError: If ``value`` is not a name, :class:`Easing`, or callable.
    """
    if isinstance(value, Easing):
        return value
    if isinstance(value, str):
        try:
            return EASINGS[value]
        except KeyError:
            raise ValueError(
                f"unknown easing {value!r}; choose one of {', '.join(sorted(EASINGS))}"
            ) from None
    if callable(value):
        return Easing(getattr(value, "__name__", "custom"), value)
    raise TypeError("easing must be a name, an Easing, or a callable")


__all__ = ["EASINGS", "EaseLike", "EaseName", "Easing", "resolve_easing"]
