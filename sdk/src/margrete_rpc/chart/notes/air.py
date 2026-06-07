from __future__ import annotations

from typing import Any, Self, cast

from ..raw import RawNote
from ..time import Tick
from .direction import AirDirection, AirDirectionLike
from .joint import AirJoint, Joint, _AirJointHost
from .shared import (
    _copy_info,
    _direction_property,
    _HeightMixin,
    _info_property,
    _note_enum_line,
    _TransformMixin,
)
from .types import ExAttr, JointKind, LongAttr, NoteInfo, NoteType


class Air:
    dir = _direction_property(AirDirection, "air")
    til = _info_property("til")

    def __init__(
        self,
        dir: AirDirectionLike,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._info = _copy_info(_info)
        self._id = _id
        self._info.type = NoteType.AIR
        self._info.long_attr = LongAttr.NONE
        self.dir = dir

    @property
    def inverted(self) -> bool:
        return self._info.ex_attr == ExAttr.INVERT

    @inverted.setter
    def inverted(self, value: bool) -> None:
        self._info.ex_attr = ExAttr.INVERT if value else ExAttr.NONE

    def validate(self) -> None:
        self.dir

    def _validate_with_anchor(self, anchor: NoteInfo) -> None:
        del anchor
        self.validate()

    def _to_raw(self, anchor: NoteInfo, *, skip_validation: bool = False) -> RawNote:
        if not skip_validation:
            self._validate_with_anchor(anchor)
        return RawNote(
            info=self._info.copy(
                type=NoteType.AIR,
                long_attr=LongAttr.NONE,
                t=anchor.t,
                x=anchor.x,
                w=anchor.w,
            ),
            _id=self._id,
        )

    def __str__(self) -> str:
        parts = [f"dir={_note_enum_line(self.dir)}"]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if self.inverted:
            parts.append("inverted=True")
        return f"Air({', '.join(parts)})"

    __repr__ = __str__


class _AttachableAirLong(_HeightMixin, _TransformMixin, _AirJointHost):
    _note_type: NoteType
    _joint_type = AirJoint

    def __init__(
        self,
        *,
        h: int,
        _air_info: NoteInfo | None = None,
        _air_id: int | None = None,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._air_info = _copy_info(_air_info)
        self._air_id = _air_id
        self._info = _copy_info(_info)
        self._id = _id
        self._joints: list[Joint] = []
        self._air_info.type = NoteType.AIR
        self._air_info.long_attr = LongAttr.NONE
        self._info.type = self._note_type
        self._info.long_attr = LongAttr.BEGIN
        if _air_info is None:
            self._air_info.direction = AirDirection.UP
            self._air_info.h = h
        if _info is None:
            self._info.h = h
        else:
            self.h = h

    def _begin_info_for_defaults(self) -> NoteInfo:
        return self._info

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        del joint
        raise NotImplementedError

    def _air_info_with_anchor(self, anchor: NoteInfo) -> NoteInfo:
        return self._air_info.copy(t=anchor.t, x=anchor.x, w=anchor.w)

    def _begin_info_with_anchor(self, anchor: NoteInfo) -> NoteInfo:
        return self._info.copy(t=anchor.t, x=anchor.x, w=anchor.w)

    def validate(self) -> None:
        self._validate_with_anchor(self._begin_info_for_defaults())

    def _validate_with_anchor(self, anchor: NoteInfo) -> None:
        self._validate_joints(self._begin_info_with_anchor(anchor))

    def _to_raw(self, anchor: NoteInfo, *, skip_validation: bool = False) -> RawNote:
        begin_info = self._begin_info_with_anchor(anchor)
        if not skip_validation:
            self._validate_joints(begin_info)
        action = RawNote(info=begin_info, _id=self._id)
        action.children = self._build_long_children(
            self._note_type,
            self._terminus_attr,
            begin_info,
            skip_validation=skip_validation,
        )
        air = RawNote(info=self._air_info_with_anchor(anchor), _id=self._air_id)
        air.children.append(action)
        return air

    def with_step(self, *, t: Tick, x: int, w: int, h: int) -> Self:
        copy = self.clone()
        copy.add_step(t=t, x=x, w=w, h=h)
        return copy

    def with_ctrl(self, *, t: Tick, x: int, w: int, h: int) -> Self:
        copy = self.clone()
        copy.add_ctrl(t=t, x=x, w=w, h=h)
        return copy

    def __str__(self) -> str:
        parts = [f"h={self.h}"]
        if self._id is not None:
            parts.append(f"id={self._id}")
        head = ", ".join(parts)
        if not self._joints:
            return f"{self.__class__.__name__}({head})"
        return f"{self.__class__.__name__}({head}, joints=[{', '.join(self._joint_strs())}])"

    __repr__ = __str__


class AirSlide(_AttachableAirLong):
    _note_type = NoteType.AIRSLIDE

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        if joint.kind is JointKind.CONTROL:
            return LongAttr.END_NOACT
        return LongAttr.END


class AirHold(_AttachableAirLong):
    _note_type = NoteType.AIRHOLD

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        if joint.kind is JointKind.CONTROL:
            return LongAttr.END_NOACT
        return LongAttr.END


class _AirAttachable:
    _air: Air | AirSlide | AirHold | None

    @property
    def air(self) -> Air | AirSlide | AirHold | None:
        return self._air

    @air.setter
    def air(self, value: AirDirectionLike | Air | AirSlide | AirHold | None) -> None:
        if value is None:
            self._air = None
            return
        if isinstance(value, (AirDirection, str)):
            value = Air(value)
        if not isinstance(value, (Air, AirSlide, AirHold)):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("air expects air direction, Air, AirSlide, or AirHold")
        self._air = value

    def with_air(self, air: AirDirectionLike | Air | AirSlide | AirHold) -> Self:
        from .transform import _clone

        new: Self = _clone(cast(Any, self))
        new.air = air
        return new

    def add_air(self, air: AirDirectionLike | Air | AirSlide | AirHold) -> Self:
        self.air = air
        return self
