from __future__ import annotations

from typing import Any, cast

from ..time import PositionLike, resolve_tick
from .air import Air, AirHold, AirSlide, _AirAttachable
from .direction import ExtapDirection, ExtapDirectionLike, FlickDirection, FlickDirectionLike
from .raw import RawNote
from .shared import (
    _check_air_matches,
    _check_tick,
    _check_width,
    _copy_info,
    _GeometryInfoMixin,
    _get_direction,
    _note_enum_line,
    _set_direction,
    _TransformMixin,
)
from .types import LongAttr, NoteInfo, NoteType


class _GroundNote(_AirAttachable, _GeometryInfoMixin, _TransformMixin):
    def __init__(
        self,
        t: int,
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
            _check_air_matches(
                int(self._air.t), self._air.x, self._air.w, int(self.t), self.x, self.w
            )

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        if not skip_validation:
            self.validate()
        note = self._base_raw()
        if self._air is not None:
            note.children.append(self._air.to_raw(skip_validation=skip_validation))
        return note


class Tap(_GroundNote):
    """A basic tap note on the ground lane.

    Ground notes are placed by timing and lane geometry: pass an absolute tick or
    :data:`Position` tuple as ``t``, a left lane index ``x``, and a width ``w``.
    An :class:`Air` note may be attached above a ground note.
    """

    def __init__(
        self,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        """Create a tap.

        Args:
            t: Absolute tick or :data:`Position` tuple.
            x: Left lane index.
            w: Width in lane units (at least 1).
        """
        super().__init__(resolve_tick(t), x, w, NoteType.TAP, _copy_info(_info), _id)

    def converted[T: (Extap, Flick, Damage)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` with this note's geometry.

        Args:
            target: The note class to convert to.
            **overrides: Field values to override on the result (e.g. ``dir=...``).
        """
        return cast(T, self._converted_to(target, **overrides))


class Damage(_GroundNote):
    """A damage (penalty) note. Same geometry as :class:`Tap`."""

    def __init__(
        self,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(resolve_tick(t), x, w, NoteType.DAMAGE, _copy_info(_info), _id)

    def converted[T: (Tap, Extap, Flick)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` with this note's geometry."""
        return cast(T, self._converted_to(target, **overrides))


class Extap(_GroundNote):
    """An ex-tap note carrying a flick :attr:`dir` direction.

    Same geometry as :class:`Tap`, plus a directional attribute. See :class:`Tap` for the
    constructor's timing/lane arguments.
    """

    @property
    def dir(self) -> ExtapDirection:
        """The note's direction (:class:`ExtapDirection`)."""
        return _get_direction(ExtapDirection, self._info)

    @dir.setter
    def dir(self, value: ExtapDirectionLike | int) -> None:
        _set_direction(ExtapDirection, "extap", self._info, value)

    def __init__(
        self,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        dir: ExtapDirectionLike | int = ExtapDirection.UP,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        """Create an ex-tap. See :class:`Tap` for ``t``/``x``/``w``; ``dir`` sets the
        flick direction (:class:`ExtapDirection`)."""
        super().__init__(resolve_tick(t), x, w, NoteType.EXTAP, _copy_info(_info), _id)
        self.dir = dir

    def _base_raw(self) -> RawNote:
        note = super()._base_raw()
        note.dir = self.dir
        return note

    def _str_parts(self) -> list[str]:
        return [*super()._str_parts(), f"dir={_note_enum_line(self.dir)}"]

    def converted[T: (Tap, Flick, Damage)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` with this note's geometry."""
        return cast(T, self._converted_to(target, **overrides))


class Flick(_GroundNote):
    """A flick note carrying a flick :attr:`dir` direction.

    Same geometry as :class:`Tap`, plus a direction (default :attr:`FlickDirection.AUTO`).
    See :class:`Tap` for the constructor's timing/lane arguments.
    """

    @property
    def dir(self) -> FlickDirection:
        """The note's flick direction (:class:`FlickDirection`)."""
        return _get_direction(FlickDirection, self._info)

    @dir.setter
    def dir(self, value: FlickDirectionLike | int) -> None:
        _set_direction(FlickDirection, "flick", self._info, value)

    def __init__(
        self,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        dir: FlickDirectionLike | int = FlickDirection.AUTO,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        """Create a flick. See :class:`Tap` for ``t``/``x``/``w``; ``dir`` sets the
        flick direction (:class:`FlickDirection`, default ``AUTO``)."""
        super().__init__(resolve_tick(t), x, w, NoteType.FLICK, _copy_info(_info), _id)
        self.dir = dir

    def _base_raw(self) -> RawNote:
        note = super()._base_raw()
        note.dir = self.dir
        return note

    def _str_parts(self) -> list[str]:
        return [*super()._str_parts(), f"dir={_note_enum_line(self.dir)}"]

    def converted[T: (Tap, Extap, Damage)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` with this note's geometry."""
        return cast(T, self._converted_to(target, **overrides))
