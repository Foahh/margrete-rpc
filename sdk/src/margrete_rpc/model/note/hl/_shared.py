from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any, Protocol, Self, runtime_checkable

from ..mg import MgNote
from ..types import AirCrushOption, NoteInfo, NoteType, direction_from_proto


class UnsupportedNoteTree(ValueError):
    pass


@runtime_checkable
class Note(Protocol):
    tick: int
    x: int
    width: int
    til: int

    @property
    def type(self) -> NoteType: ...

    def shift(self, *, t: int = 0, x: int = 0, w: int = 0, h: int = 0) -> Self: ...

    def to_mg(self, *, skip_validation: bool = False) -> MgNote: ...


def _note_enum_line(value: IntEnum | StrEnum | int) -> str:
    if isinstance(value, (IntEnum, StrEnum)):
        return f"{type(value).__name__}.{value.name}({value.value!r})"
    return repr(value)


def _check_tick(tick: int) -> None:
    if int(tick) < 0:
        raise ValueError("tick must be non-negative")


def _check_width(width: int) -> None:
    if width < 1:
        raise ValueError("width must be at least 1")


def _copy_info(info: NoteInfo | None) -> NoteInfo:
    return info.copy() if info is not None else NoteInfo()


def _stored_value(value: Any) -> Any:
    return int(value) if isinstance(value, IntEnum) else value


def _enum_value(enum_type: type[IntEnum], value: int) -> IntEnum | int:
    try:
        return enum_type(value)
    except ValueError:
        return value


def _info_value(value: Any, enum_type: type[IntEnum] | None) -> Any:
    if enum_type is None:
        return _stored_value(value)
    try:
        return enum_type(value)
    except ValueError:
        return _stored_value(value)


def _info_property(name: str, enum_type: type[IntEnum] | None = None):
    def getter(self):
        value = getattr(self._info, name)
        return _enum_value(enum_type, value) if enum_type is not None else value

    def setter(self, value):
        setattr(self._info, name, _info_value(value, enum_type))

    return property(getter, setter)


def _checked_info_property(name: str, check):
    def getter(self):
        return getattr(self._info, name)

    def setter(self, value):
        check(value)
        setattr(self._info, name, value)

    return property(getter, setter)


def _tick_property():
    def getter(self):
        return self._info.tick

    def setter(self, value):
        self._info.tick = value
        _check_tick(self._info.tick)

    return property(getter, setter)


def _direction_property(enum_type: type[StrEnum], label: str):
    def getter(self):
        value = self._info.direction
        if isinstance(value, enum_type):
            return value
        if isinstance(value, str):
            return enum_type(value)
        return direction_from_proto(self._info.type, int(value))

    def setter(self, value):
        try:
            if isinstance(value, str):
                direction = enum_type(value)
            else:
                direction = direction_from_proto(self._info.type, int(value))
                if not isinstance(direction, enum_type):
                    raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid {label} direction") from exc
        self._info.direction = direction

    return property(getter, setter)


def _coerce_aircrush_density_value(value: object) -> int:
    if isinstance(value, AirCrushOption):
        return int(value)
    if type(value) is int:
        return value
    raise TypeError(f"density must be int or AirCrushOption, got {type(value).__name__}")


class _GeometryInfoMixin:
    tick = _tick_property()
    x = _info_property("x")
    width = _checked_info_property("width", _check_width)
    til = _info_property("timeline_id")


class _HeightMixin:
    height = _info_property("height")


class _ShiftMixin:
    def shift(self, *, t: int = 0, x: int = 0, w: int = 0, h: int = 0) -> Self:
        from ..shift import _shift_note

        return _shift_note(self, t=t, x=x, w=w, h=h)
