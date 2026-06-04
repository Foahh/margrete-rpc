from __future__ import annotations

from ...chart_time import Tick
from ..mg import MgNote
from ..types import (
    ExtapDirection,
    ExtapDirectionLike,
    FlickDirection,
    FlickDirectionLike,
    LongAttr,
    NoteInfo,
    NoteType,
)
from ._air import Air, AirHold, AirSlide, _AirAttachable
from ._shared import (
    _check_tick,
    _check_width,
    _copy_info,
    _direction_property,
    _GeometryInfoMixin,
    _note_enum_line,
    _ShiftMixin,
)


class _GroundNote(_AirAttachable, _GeometryInfoMixin, _ShiftMixin):
    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
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
        self.tick = tick
        self.x = x
        self.width = width
        _check_tick(self.tick)
        _check_width(self.width)

    @property
    def type(self) -> NoteType:
        return self._type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.NONE

    def _base_mg(self) -> MgNote:
        return MgNote(info=self._info.copy(), _id=self._id)

    def _str_parts(self) -> list[str]:
        return [
            f"tick={int(self.tick)}",
            f"x={self.x}",
            f"width={self.width}",
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

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        note = self._base_mg()
        if self._air is not None:
            note.children.append(self._air._to_mg(note.info, skip_validation=skip_validation))
        return note


class Tap(_GroundNote):
    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.TAP, _copy_info(_info), _id)


class Damage(_GroundNote):
    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.DAMAGE, _copy_info(_info), _id)


class Extap(_GroundNote):
    direction = _direction_property(ExtapDirection, "extap")

    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        *,
        direction: ExtapDirectionLike | int = ExtapDirection.UP,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.EXTAP, _copy_info(_info), _id)
        self.direction = direction

    def _base_mg(self) -> MgNote:
        note = super()._base_mg()
        note.direction = self.direction
        return note

    def _str_parts(self) -> list[str]:
        return [*super()._str_parts(), f"direction={_note_enum_line(self.direction)}"]


class Flick(Extap):
    direction = _direction_property(FlickDirection, "flick")

    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        *,
        direction: FlickDirectionLike | int = FlickDirection.AUTO,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, direction=direction, _info=_info, _id=_id)
        self._type = NoteType.FLICK
        self._info.type = NoteType.FLICK
