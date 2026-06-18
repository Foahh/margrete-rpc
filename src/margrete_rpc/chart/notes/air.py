from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, cast

from ..time import PositionLike, resolve_tick
from .direction import AirDirection, AirDirectionLike
from .joint import AirJoint, Joint, _AirJointHost
from .raw import RawNote
from .shared import (
    _check_tick,
    _check_width,
    _copy_info,
    _GeometryInfoMixin,
    _get_direction,
    _HeightMixin,
    _note_enum_line,
    _set_direction,
    _TransformMixin,
)
from .types import ExAttr, JointKind, LongAttr, NoteInfo, NoteType

if TYPE_CHECKING:
    from .ground import Damage, Extap, Flick, Tap
    from .long import AirCrush, Slide


class Air(_GeometryInfoMixin, _TransformMixin):
    """An air note: an upward/diagonal flick attached above a ground note.

    Its geometry (``t``/``p``, ``x``, ``w``) must match the ground note it is attached to
    (see :attr:`_AirAttachable.air`). Carries a :attr:`dir` direction and an
    :attr:`inverted` flag.
    """

    __slots__ = ("_info", "_id")

    @property
    def dir(self) -> AirDirection:
        """The air direction (:class:`AirDirection`)."""
        return _get_direction(AirDirection, self._info)

    @dir.setter
    def dir(self, value: AirDirectionLike | int) -> None:
        _set_direction(AirDirection, "air", self._info, value)

    def __init__(
        self,
        dir: AirDirectionLike | int,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        """Create an air note.

        Args:
            dir: Air direction (:class:`AirDirection`).
            t: Absolute tick or :data:`Position` tuple (must match the host ground note).
            x: Left lane index (must match the host ground note).
            w: Width in lane units (must match the host ground note).
        """
        self._info = _copy_info(_info)
        self._id = _id
        self._info.type = NoteType.AIR
        self._info.long_attr = LongAttr.NONE
        self.t = resolve_tick(t)
        self.x = x
        self.w = w
        self.dir = dir

    @property
    def inverted(self) -> bool:
        """Whether the air note is inverted (downward)."""
        return self._info.ex_attr == ExAttr.INVERT

    @inverted.setter
    def inverted(self, value: bool) -> None:
        self._info.ex_attr = ExAttr.INVERT if value else ExAttr.NONE

    def validate(self) -> None:
        _check_tick(self.t)
        _check_width(self.w)
        self.dir

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        if not skip_validation:
            self.validate()
        return RawNote(info=self._info.copy(), _id=self._id)

    def converted[T: (Tap, Extap, Flick, Damage)](self, target: type[T], **overrides: Any) -> T:
        """Return a new ground note of type ``target`` with this air note attached."""
        return cast(T, self._converted_to(target, **overrides))

    def __str__(self) -> str:
        parts = [
            f"t={int(self.t)}",
            f"x={self.x}",
            f"w={self.w}",
            f"dir={_note_enum_line(self.dir)}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if self.inverted:
            parts.append("inverted=True")
        return f"Air({', '.join(parts)})"

    __repr__ = __str__


class _AttachableAirLong(_GeometryInfoMixin, _HeightMixin, _TransformMixin, _AirJointHost):
    __slots__ = ("_info", "_id", "_joints", "_inverted")

    _note_type: NoteType
    _joint_type = AirJoint

    def __init__(
        self,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        h: int,
        inverted: bool = False,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._info = _copy_info(_info)
        self._id = _id
        self._joints: list[Joint] = []
        self._inverted = bool(inverted)
        self._info.type = self._note_type
        self._info.long_attr = LongAttr.BEGIN
        self.t = resolve_tick(t)
        self.x = x
        self.w = w
        self.h = h

    @property
    def inverted(self) -> bool:
        """Whether the long air note is inverted (downward)."""
        return self._inverted

    @inverted.setter
    def inverted(self, value: bool) -> None:
        self._inverted = bool(value)

    def _begin_info_for_defaults(self) -> NoteInfo:
        return self._info

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        del joint
        raise NotImplementedError

    def validate(self) -> None:
        _check_tick(self.t)
        _check_width(self.w)
        self._validate_joints(self._info)

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        if not skip_validation:
            self._validate_joints(self._info)
        action = RawNote(info=self._info.copy(), _id=self._id)
        action.children = self._build_long_children(
            self._note_type,
            self._terminus_attr,
            self._info,
            skip_validation=skip_validation,
        )
        air_info = self._info.copy(
            type=NoteType.AIR,
            long_attr=LongAttr.NONE,
            direction=AirDirection.UP,
            ex_attr=ExAttr.INVERT if self.inverted else ExAttr.NONE,
        )
        air = RawNote(info=air_info, _id=None)
        air.children.append(action)
        return air

    def with_step(self, *, t: int | PositionLike, x: int, w: int, h: int) -> Self:
        """Return a copy with a step joint appended at the given timing and geometry."""
        copy = self.clone()
        copy.add_step(t=t, x=x, w=w, h=h)
        return copy

    def with_ctrl(self, *, t: int | PositionLike, x: int, w: int, h: int) -> Self:
        """Return a copy with a control joint appended at the given timing and geometry."""
        copy = self.clone()
        copy.add_ctrl(t=t, x=x, w=w, h=h)
        return copy

    def __str__(self) -> str:
        parts = [f"t={int(self.t)}", f"x={self.x}", f"w={self.w}", f"h={self.h}"]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if self.inverted:
            parts.append("inverted=True")
        head = ", ".join(parts)
        if not self._joints:
            return f"{self.__class__.__name__}({head})"
        return f"{self.__class__.__name__}({head}, joints=[{', '.join(self._joint_strs())}])"

    __repr__ = __str__


class AirSlide(_AttachableAirLong):
    """An air slide: a long air note threading through joints, each carrying height ``h``.

    Construct with the begin geometry (including ``h``), then add joints with
    :meth:`add_step` / :meth:`add_ctrl` or their copy-returning ``with_*`` forms. May be
    attached above a ground note like a plain :class:`Air`.
    """

    __slots__ = ()

    _note_type = NoteType.AIRSLIDE

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        if joint.kind is JointKind.CONTROL:
            return LongAttr.END_NOACT
        return LongAttr.END

    def converted[T: (Slide, AirCrush)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` carrying this note's geometry and joints."""
        return cast(T, self._converted_to(target, **overrides))


class AirHold(_AttachableAirLong):
    """An air hold: a long air note held through joints, each carrying height ``h``.

    Like :class:`AirSlide` in construction; see :meth:`add_step` / :meth:`add_ctrl`.
    """

    __slots__ = ()

    _note_type = NoteType.AIRHOLD

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        if joint.kind is JointKind.CONTROL:
            return LongAttr.END_NOACT
        return LongAttr.END

    def converted[T: (Slide, AirSlide, AirCrush)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` carrying this note's geometry and joints."""
        return cast(T, self._converted_to(target, **overrides))


class _AirAttachable:
    """Mixin giving ground notes an optional attached air note.

    Provides the :attr:`air` slot plus :meth:`add_air` (in place) and :meth:`with_air`
    (returns a copy). The attached air's geometry must match the host note.
    """

    __slots__ = ()

    _air: Air | AirSlide | AirHold | None

    @property
    def air(self) -> Air | AirSlide | AirHold | None:
        """The attached air note (:class:`Air`, :class:`AirSlide`, or :class:`AirHold`), or
        ``None``."""
        return self._air

    @air.setter
    def air(self, value: Air | AirSlide | AirHold | None) -> None:
        if value is None:
            self._air = None
            return
        if not isinstance(value, (Air, AirSlide, AirHold)):
            raise TypeError("air expects Air, AirSlide, or AirHold")
        self._air = value

    def with_air(self, air: Air | AirSlide | AirHold) -> Self:
        """Return a copy of this note with ``air`` attached, leaving the original unchanged."""
        from .transform import _clone

        new: Self = _clone(cast(Any, self))
        new.air = air
        return new

    def add_air(self, air: Air | AirSlide | AirHold) -> Self:
        """Attach ``air`` to this note in place and return ``self``."""
        self.air = air
        return self
