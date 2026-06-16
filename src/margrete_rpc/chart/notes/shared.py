from __future__ import annotations

from collections.abc import Callable
from enum import IntEnum, StrEnum
from typing import Any, Literal, Protocol, Self, cast, runtime_checkable

from ..constants import STANDARD_FIELD_WIDTH
from ..time import DivisionLike, Position, PositionLike
from .direction import direction_from_proto
from .raw import RawNote
from .types import NoteInfo

type Delta = int | Callable[[int], int]

type AlignMode = Literal["round", "floor", "ceil"]


class UnsupportedNoteTree(ValueError):
    """Raised when a :class:`RawNote` tree cannot be wrapped into a typed note."""


@runtime_checkable
class Note(Protocol):
    """The common interface implemented by every typed note.

    Notes expose geometry (timing ``t``/``p``, lane ``x``, width ``w``) and a set of
    transforms. Each transform comes in two forms: the bare verb (e.g. :meth:`shift`)
    mutates the note in place and returns ``self`` for chaining, while the past-tense form
    (e.g. :meth:`shifted`) returns a transformed :meth:`clone` and leaves the original
    untouched.
    """

    @property
    def t(self) -> int:
        """Absolute tick of the note from the chart start."""
        ...

    @t.setter
    def t(self, value: int | PositionLike) -> None: ...

    @property
    def p(self) -> Position:
        """Timing as a ``(bar, beat, offset)`` :class:`Position`; the read-only view of ``t``."""
        ...

    @property
    def x(self) -> int:
        """Left lane index of the note."""
        ...

    @property
    def w(self) -> int:
        """Width of the note in lane units (at least 1)."""
        ...

    @property
    def til(self) -> int:
        """Timeline id the note belongs to."""
        ...

    def shift(
        self, *, t: Delta | PositionLike = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0
    ) -> Self:
        """Move/resize the note in place and return ``self``.

        Each delta is either an int added to the field, or a callable mapping the current
        value to a new one. Pass a :data:`Position` tuple for ``t`` to shift timing by a
        musical position delta.

        Args:
            t: Tick delta, callable, or :data:`Position` tuple for a position-based shift.
            x: Lane delta.
            w: Width delta.
            h: Air-height delta (for notes with height).
        """
        ...

    def shifted(
        self, *, t: Delta | PositionLike = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0
    ) -> Self:
        """Return a :meth:`clone` shifted by the given deltas, leaving ``self`` unchanged."""
        ...

    def scale(self, factor: float, *, pivot: int | PositionLike = 0) -> Self:
        """Scale the note's timing about ``pivot`` by ``factor``, in place; returns ``self``."""
        ...

    def scaled(self, factor: float, *, pivot: int | PositionLike = 0) -> Self:
        """Return a :meth:`clone` scaled about ``pivot``, leaving ``self`` unchanged."""
        ...

    def align(self, interval: int | DivisionLike, *, mode: AlignMode = "round") -> Self:
        """Snap the note's timing to a multiple of ``interval``, in place; returns ``self``.

        Args:
            interval: Grid spacing in ticks, or a :data:`DivisionLike` resolved to ticks.
            mode: How to snap: ``"round"`` (nearest), ``"floor"``, or ``"ceil"``.
        """
        ...

    def aligned(self, interval: int | DivisionLike, *, mode: AlignMode = "round") -> Self:
        """Return a :meth:`clone` aligned to ``interval``, leaving ``self`` unchanged."""
        ...

    def flip(self, *, field: int = STANDARD_FIELD_WIDTH) -> Self:
        """Mirror the note horizontally within ``field`` lanes, in place; returns ``self``."""
        ...

    def flipped(self, *, field: int = STANDARD_FIELD_WIDTH) -> Self:
        """Return a :meth:`clone` flipped within ``field``, leaving ``self`` unchanged."""
        ...

    def clamp(self, *, left: int = 0, right: int = STANDARD_FIELD_WIDTH) -> Self:
        """Clamp the note's lane extent to ``[left, right)``, in place; returns ``self``.

        Args:
            left: Inclusive left boundary lane index (default 0).
            right: Exclusive right boundary lane index (default :data:`STANDARD_FIELD_WIDTH`).
        """
        ...

    def clamped_w(self, *, left: int = 0, right: int = STANDARD_FIELD_WIDTH) -> Self:
        """Return a :meth:`clone` with the lane extent clamped, leaving ``self`` unchanged."""
        ...

    def clone(self) -> Self:
        """Return a deep copy of the note (without its server-assigned id)."""
        ...

    def validate(self) -> None:
        """Check the note's geometry, raising ``ValueError`` if it is invalid."""
        ...

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        """Convert the note to its :class:`RawNote` protobuf-tree form.

        Args:
            skip_validation: Skip the :meth:`validate` check before converting.
        """
        ...


def _note_enum_line(value: object) -> str:
    if isinstance(value, (IntEnum, StrEnum)):
        return f"{type(value).__name__}.{value.name}({value.value!r})"
    return repr(value)


def _check_tick(t: int) -> None:
    if int(t) < 0:
        raise ValueError("t must be non-negative")


def _check_width(w: int) -> None:
    if w < 1:
        raise ValueError("w must be at least 1")


def _check_air_matches(
    air_t: int, air_x: int, air_w: int, ref_t: int, ref_x: int, ref_w: int
) -> None:
    if air_t != ref_t or air_x != ref_x or air_w != ref_w:
        raise ValueError(
            f"air geometry (t={air_t}, x={air_x}, w={air_w}) "
            f"does not match parent (t={ref_t}, x={ref_x}, w={ref_w})"
        )


def _copy_info(info: NoteInfo | None) -> NoteInfo:
    return info.copy() if info is not None else NoteInfo()


def _get_direction[E: StrEnum](enum_type: type[E], info: NoteInfo) -> E:
    value = info.direction
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        return enum_type(value)
    return cast(E, direction_from_proto(info.type, int(value)))


def _set_direction[E: StrEnum](
    enum_type: type[E], label: str, info: NoteInfo, value: E | str | int
) -> None:
    try:
        if isinstance(value, str):
            direction: E = enum_type(value)
        else:
            result = direction_from_proto(info.type, int(value))
            if not isinstance(result, enum_type):
                raise ValueError
            direction = result
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {label} direction") from exc
    info.direction = direction


class _GeometryInfoMixin:
    __slots__ = ()

    _info: NoteInfo

    @property
    def t(self) -> int:
        return self._info.t

    @t.setter
    def t(self, value: int | PositionLike) -> None:
        self._info.t = value
        _check_tick(self._info.t)

    @property
    def p(self) -> Position:
        return self._info.p

    @property
    def x(self) -> int:
        return self._info.x

    @x.setter
    def x(self, value: int) -> None:
        self._info.x = value

    @property
    def w(self) -> int:
        return self._info.w

    @w.setter
    def w(self, value: int) -> None:
        _check_width(value)
        self._info.w = value

    @property
    def til(self) -> int:
        return self._info.til

    @til.setter
    def til(self, value: int) -> None:
        self._info.til = value


class _HeightMixin:
    __slots__ = ()

    _info: NoteInfo

    @property
    def h(self) -> int:
        return self._info.h

    @h.setter
    def h(self, value: int) -> None:
        self._info.h = value


class _TransformMixin:
    __slots__ = ()

    _info: NoteInfo
    _id: int | None

    def shift(
        self, *, t: Delta | PositionLike = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0
    ) -> Self:
        from .shift import _resolve_shift_delta, _shift_note

        return cast(Self, _shift_note(self, t=_resolve_shift_delta(t), x=x, w=w, h=h))

    def shifted(
        self, *, t: Delta | PositionLike = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0
    ) -> Self:
        return self.clone().shift(t=t, x=x, w=w, h=h)

    def scale(self, factor: float, *, pivot: int | PositionLike = 0) -> Self:
        from .transform import _scale

        return cast(Self, _scale(cast(Any, self), factor, pivot))

    def scaled(self, factor: float, *, pivot: int | PositionLike = 0) -> Self:
        return self.clone().scale(factor, pivot=pivot)

    def align(self, interval: int | DivisionLike, *, mode: AlignMode = "round") -> Self:
        from .transform import _align

        return cast(Self, _align(cast(Any, self), interval, mode))

    def aligned(self, interval: int | DivisionLike, *, mode: AlignMode = "round") -> Self:
        return self.clone().align(interval, mode=mode)

    def flip(self, *, field: int = STANDARD_FIELD_WIDTH) -> Self:
        from .transform import _flip

        return cast(Self, _flip(cast(Any, self), field))

    def flipped(self, *, field: int = STANDARD_FIELD_WIDTH) -> Self:
        return self.clone().flip(field=field)

    def clamp(self, *, left: int = 0, right: int = STANDARD_FIELD_WIDTH) -> Self:
        from .transform import _clamp

        return cast(Self, _clamp(cast(Any, self), left, right))

    def clamped_w(self, *, left: int = 0, right: int = STANDARD_FIELD_WIDTH) -> Self:
        return self.clone().clamp(left=left, right=right)

    def clone(self) -> Self:
        from .transform import _clone

        return cast(Self, _clone(cast(Any, self)))

    def _converted_to(self, target: type[object], **overrides: Any) -> Any:
        from .transform import _convert

        return _convert(cast(Any, self), cast(Any, target), overrides)
