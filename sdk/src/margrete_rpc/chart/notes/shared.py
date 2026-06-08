from __future__ import annotations

from collections.abc import Callable
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, Literal, Protocol, Self, cast, overload, runtime_checkable

from ..raw import RawNote
from ..time import Tick
from .direction import direction_from_proto
from .types import NoteInfo

if TYPE_CHECKING:
    from .air import AirHold, AirSlide
    from .ground import Damage, Extap, Flick, Tap
    from .long import AirCrush, Hold, Slide

FIELD_WIDTH = 16

type Delta = int | Callable[[int], int]

type AlignMode = Literal["round", "floor", "ceil"]


class UnsupportedNoteTree(ValueError):
    pass


@runtime_checkable
class Note(Protocol):
    t: int
    x: int
    w: int
    til: int

    def shift(self, *, t: Delta = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0) -> Self: ...

    def shifted(self, *, t: Delta = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0) -> Self: ...

    def scale(self, factor: float, *, pivot: int | Tick = 0) -> Self: ...

    def scaled(self, factor: float, *, pivot: int | Tick = 0) -> Self: ...

    def align(self, interval: int | Tick, *, mode: AlignMode = "round") -> Self: ...

    def aligned(self, interval: int | Tick, *, mode: AlignMode = "round") -> Self: ...

    def flip(self, *, field: int = FIELD_WIDTH) -> Self: ...

    def flipped(self, *, field: int = FIELD_WIDTH) -> Self: ...

    def clone(self) -> Self: ...

    def converted[T: Note](self, target: type[T], **overrides: Any) -> T: ...

    def validate(self) -> None: ...

    def to_raw(self, *, skip_validation: bool = False) -> RawNote: ...


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


def _check_air_matches(air_t: int, air_x: int, air_w: int, ref_t: int, ref_x: int, ref_w: int) -> None:
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
    return direction_from_proto(info.type, int(value))


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
    _info: NoteInfo

    @property
    def t(self) -> int:
        return self._info.t

    @t.setter
    def t(self, value: int | Tick) -> None:
        self._info.t = value
        _check_tick(self._info.t)

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
    _info: NoteInfo

    @property
    def h(self) -> int:
        return self._info.h

    @h.setter
    def h(self, value: int) -> None:
        self._info.h = value


class _TransformMixin:
    _info: NoteInfo
    _id: int | None

    def shift(self, *, t: Delta = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0) -> Self:
        from .shift import _shift_note

        return _shift_note(self, t=t, x=x, w=w, h=h)

    def shifted(self, *, t: Delta = 0, x: Delta = 0, w: Delta = 0, h: Delta = 0) -> Self:
        return self.clone().shift(t=t, x=x, w=w, h=h)

    def scale(self, factor: float, *, pivot: int | Tick = 0) -> Self:
        from .transform import _scale

        return _scale(self, factor, pivot)

    def scaled(self, factor: float, *, pivot: int | Tick = 0) -> Self:
        return self.clone().scale(factor, pivot=pivot)

    def align(self, interval: int | Tick, *, mode: AlignMode = "round") -> Self:
        from .transform import _align

        return _align(self, interval, mode)

    def aligned(self, interval: int | Tick, *, mode: AlignMode = "round") -> Self:
        return self.clone().align(interval, mode=mode)

    def flip(self, *, field: int = FIELD_WIDTH) -> Self:
        from .transform import _flip

        return _flip(self, field)

    def flipped(self, *, field: int = FIELD_WIDTH) -> Self:
        return self.clone().flip(field=field)

    def clone(self) -> Self:
        from .transform import _clone

        return _clone(self)

    @overload
    def converted[T: (Extap, Flick, Damage)](
        self: Tap,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (Tap, Flick, Damage)](
        self: Extap,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (Tap, Extap, Damage)](
        self: Flick,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (Tap, Extap, Flick)](
        self: Damage,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (AirSlide, AirCrush)](
        self: Slide,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (Slide, AirCrush)](
        self: AirSlide,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (Slide, AirSlide)](
        self: AirCrush,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    @overload
    def converted[T: (Slide, AirSlide, AirCrush, AirHold)](
        self: Hold,
        target: type[T],
        **overrides: Any,
    ) -> T: ...

    def converted(self: object, target: type[object], **overrides: Any) -> Any:
        from .transform import _convert

        return _convert(cast(Any, self), cast(Any, target), overrides)
