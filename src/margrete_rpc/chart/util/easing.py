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

_BISECT_ITERS = 48


@dataclass(frozen=True, slots=True)
class Easing:
    """A ``[0,1] -> [0,1]`` easing curve with a forward ``solve`` and an :meth:`inverse`.

    Custom easings must be monotonic non-decreasing with ``solve(0) == 0`` and ``solve(1) == 1``.
    """

    name: str
    solve: Callable[[float], float]
    _inverse: Callable[[float], float] | None = None

    def inverse(self, y: float) -> float:
        """Map an eased value ``y in [0,1]`` back to its progress ``t in [0,1]``."""
        if self._inverse is not None:
            return self._inverse(y)
        lo, hi = 0.0, 1.0
        for _ in range(_BISECT_ITERS):
            mid = (lo + hi) / 2
            if self.solve(mid) < y:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2


def _power(n: int) -> tuple[Easing, Easing, Easing]:
    inv_n = 1.0 / n

    def in_(t: float) -> float:
        return t**n

    def in_inv(y: float) -> float:
        return y**inv_n

    def out(t: float) -> float:
        return 1.0 - (1.0 - t) ** n

    def out_inv(y: float) -> float:
        return 1.0 - (1.0 - y) ** inv_n

    def in_out(t: float) -> float:
        if t < 0.5:
            return (2.0 * t) ** n / 2.0
        return 1.0 - (2.0 - 2.0 * t) ** n / 2.0

    def in_out_inv(y: float) -> float:
        if y < 0.5:
            return (2.0 * y) ** inv_n / 2.0
        return 1.0 - (2.0 - 2.0 * y) ** inv_n / 2.0

    family = {2: "quad", 3: "cubic", 4: "quart", 5: "quint"}[n]
    return (
        Easing(f"in_{family}", in_, in_inv),
        Easing(f"out_{family}", out, out_inv),
        Easing(f"in_out_{family}", in_out, in_out_inv),
    )


def _sine() -> tuple[Easing, Easing, Easing]:
    half_pi = math.pi / 2.0

    return (
        Easing(
            "in_sine",
            lambda t: 1.0 - math.cos(t * half_pi),
            lambda y: math.acos(1.0 - y) / half_pi,
        ),
        Easing(
            "out_sine",
            lambda t: math.sin(t * half_pi),
            lambda y: math.asin(y) / half_pi,
        ),
        Easing(
            "in_out_sine",
            lambda t: (1.0 - math.cos(math.pi * t)) / 2.0,
            lambda y: math.acos(1.0 - 2.0 * y) / math.pi,
        ),
    )


def _circ() -> tuple[Easing, Easing, Easing]:
    def in_(t: float) -> float:
        return 1.0 - math.sqrt(1.0 - t * t)

    def in_inv(y: float) -> float:
        return math.sqrt(1.0 - (1.0 - y) ** 2)

    def out(t: float) -> float:
        return math.sqrt(1.0 - (1.0 - t) ** 2)

    def out_inv(y: float) -> float:
        return 1.0 - math.sqrt(1.0 - y * y)

    def in_out(t: float) -> float:
        if t < 0.5:
            return (1.0 - math.sqrt(1.0 - (2.0 * t) ** 2)) / 2.0
        return (math.sqrt(1.0 - (2.0 - 2.0 * t) ** 2) + 1.0) / 2.0

    def in_out_inv(y: float) -> float:
        if y < 0.5:
            return math.sqrt(1.0 - (1.0 - 2.0 * y) ** 2) / 2.0
        return 1.0 - math.sqrt(1.0 - (2.0 * y - 1.0) ** 2) / 2.0

    return (
        Easing("in_circ", in_, in_inv),
        Easing("out_circ", out, out_inv),
        Easing("in_out_circ", in_out, in_out_inv),
    )


def _expo() -> tuple[Easing, Easing, Easing]:
    def in_(t: float) -> float:
        return 0.0 if t <= 0.0 else 2.0 ** (10.0 * t - 10.0)

    def in_inv(y: float) -> float:
        return 0.0 if y <= 0.0 else (math.log2(y) + 10.0) / 10.0

    def out(t: float) -> float:
        return 1.0 if t >= 1.0 else 1.0 - 2.0 ** (-10.0 * t)

    def out_inv(y: float) -> float:
        return 1.0 if y >= 1.0 else -math.log2(1.0 - y) / 10.0

    def in_out(t: float) -> float:
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        if t < 0.5:
            return 2.0 ** (20.0 * t - 10.0) / 2.0
        return (2.0 - 2.0 ** (-20.0 * t + 10.0)) / 2.0

    def in_out_inv(y: float) -> float:
        if y <= 0.0:
            return 0.0
        if y >= 1.0:
            return 1.0
        if y < 0.5:
            return (math.log2(2.0 * y) + 10.0) / 20.0
        return (10.0 - math.log2(2.0 - 2.0 * y)) / 20.0

    return (
        Easing("in_expo", in_, in_inv),
        Easing("out_expo", out, out_inv),
        Easing("in_out_expo", in_out, in_out_inv),
    )


def _build_registry() -> dict[str, Easing]:
    registry: dict[str, Easing] = {"linear": Easing("linear", lambda t: t, lambda y: y)}
    for easing in (*_sine(), *_power(2), *_power(3), *_power(4), *_power(5), *_expo(), *_circ()):
        registry[easing.name] = easing
    return registry


EASINGS: dict[str, Easing] = _build_registry()
"""Built-in easings keyed by name (see :data:`EaseName`).

Includes ``linear`` and the ``in_`` / ``out_`` / ``in_out_`` variants of ``sine``, ``quad``,
``cubic``, ``quart``, ``quint``, ``expo``, and ``circ``."""


def resolve_easing(value: EaseLike) -> Easing:
    """Resolve an :data:`EaseLike` to an :class:`Easing`.

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
        return Easing(getattr(value, "__name__", "custom"), value, None)
    raise TypeError("easing must be a name, an Easing, or a callable")


__all__ = ["EASINGS", "EaseLike", "EaseName", "Easing", "resolve_easing"]
