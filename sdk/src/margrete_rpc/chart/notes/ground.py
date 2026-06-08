from __future__ import annotations

from typing import cast

from ..raw import RawNote
from ..time import Tick
from .air import Air, AirHold, AirSlide, _AirAttachable
from .direction import ExtapDirection, ExtapDirectionLike, FlickDirection, FlickDirectionLike
from .shared import (
    _check_air_matches,
    _check_tick,
    _check_width,
    _copy_info,
    _direction_property,
    _GeometryInfoMixin,
    _note_enum_line,
    _TransformMixin,
)
from .types import LongAttr, NoteInfo, NoteType


class _GroundNote(_AirAttachable, _GeometryInfoMixin, _TransformMixin):
    def __init__(
        self,
        t: Tick,
        x: int,
        w: int,
        _type: NoteType,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._type = _type
        self._info = _copy_info(_info)
        self._id = _id
        self._air: Air | AirSlide | AirHold | None = None
        self._info.type = _type
        self._info.long_attr = LongAttr.NONE
        self.t = t
        self.x = x
        self.w = w
        _check_tick(self.t)
        _check_width(self.w)

    def _base_raw(self) -> RawNote:
        return RawNote(info=self._info.copy(), _id=self._id)

    def _str_parts(self) -> list[str]:
        return [
            f"t={int(self.t)}",
            f"x={self.x}",
            f"w={self.w}",
        ]

    def __str__(self) -> str:
        parts = self._str_parts()
        if self._id is not None:
            parts.append(f"id={self._id}")
        head = ", ".join(parts)
        if self._air is None:
            return f"{self.__class__.__name__}({head})"
        air_lines = str(self._air).splitlines()
        return f"{self.__class__.__name__}({head})\n" + "\n".join(f"  {line}" for line in air_lines)

    __repr__ = __str__

    def validate(self) -> None:
        _check_tick(self.t)
        _check_width(self.w)
        if self._air is not None:
            self._air.validate()
            _check_air_matches(int(self._air.t), self._air.x, self._air.w, int(self.t), self.x, self.w)

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        if not skip_validation:
            self.validate()
        note = self._base_raw()
        if self._air is not None:
            note.children.append(self._air.to_raw(skip_validation=skip_validation))
        return note


class Tap(_GroundNote):
    def __init__(
        self,
        *,
        t: Tick,
        x: int,
        w: int,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(t, x, w, NoteType.TAP, _copy_info(_info), _id)


class Damage(_GroundNote):
    def __init__(
        self,
        *,
        t: Tick,
        x: int,
        w: int,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(t, x, w, NoteType.DAMAGE, _copy_info(_info), _id)


class Extap(_GroundNote):
    dir = _direction_property(ExtapDirection, "extap")

    def __init__(
        self,
        *,
        t: Tick,
        x: int,
        w: int,
        dir: ExtapDirectionLike | int = ExtapDirection.UP,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(t, x, w, NoteType.EXTAP, _copy_info(_info), _id)
        self.dir = dir

    def _base_raw(self) -> RawNote:
        note = super()._base_raw()
        note.dir = self.dir
        return note

    def _str_parts(self) -> list[str]:
        return [*super()._str_parts(), f"dir={_note_enum_line(self.dir)}"]


class Flick(Extap):
    dir = _direction_property(FlickDirection, "flick")

    def __init__(
        self,
        *,
        t: Tick,
        x: int,
        w: int,
        dir: FlickDirectionLike | int = FlickDirection.AUTO,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(
            t=t, x=x, w=w, dir=cast("ExtapDirectionLike | int", dir), _info=_info, _id=_id
        )
        self._type = NoteType.FLICK
        self._info.type = NoteType.FLICK
