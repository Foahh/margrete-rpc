from __future__ import annotations

from typing import Self

from margrete_rpc._warnings import warnings

from ..time import Tick
from ._joint import AirJoint, Joint, _JointHost
from ._shared import (
    _copy_info,
    _direction_property,
    _HeightMixin,
    _info_property,
    _note_enum_line,
)
from .direction import AirDirection, AirDirectionLike
from .node import Node
from .types import ExAttr, JointKind, LongAttr, NoteInfo, NoteType


class Air:
    direction = _direction_property(AirDirection, "air")
    til = _info_property("til")

    def __init__(
        self,
        direction: AirDirectionLike,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._info = _copy_info(_info)
        self._id = _id
        self._info.type = NoteType.AIR
        self._info.long_attr = LongAttr.NONE
        self.direction = direction

    @property
    def inverted(self) -> bool:
        return self._info.ex_attr == ExAttr.INVERT

    @inverted.setter
    def inverted(self, value: bool) -> None:
        self._info.ex_attr = ExAttr.INVERT if value else ExAttr.NONE

    @property
    def type(self) -> NoteType:
        return NoteType.AIR

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.NONE

    def validate(self) -> None:
        self.direction

    def _validate_with_anchor(self, anchor: NoteInfo) -> None:
        del anchor
        self.validate()

    def _to_node(self, anchor: NoteInfo, *, skip_validation: bool = False) -> Node:
        if not skip_validation:
            self._validate_with_anchor(anchor)
        return Node(
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
        parts = [f"direction={_note_enum_line(self.direction)}"]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if self.inverted:
            parts.append("inverted=True")
        return f"Air({', '.join(parts)})"

    __repr__ = __str__


class _AttachableAirLong(_HeightMixin, _JointHost):
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

    @property
    def type(self) -> NoteType:
        return self._note_type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.BEGIN

    def _air_info_with_anchor(self, anchor: NoteInfo) -> NoteInfo:
        return self._air_info.copy(t=anchor.t, x=anchor.x, w=anchor.w)

    def _begin_info_with_anchor(self, anchor: NoteInfo) -> NoteInfo:
        return self._info.copy(t=anchor.t, x=anchor.x, w=anchor.w)

    def validate(self) -> None:
        self._validate_with_anchor(self._begin_info_for_defaults())

    def _validate_with_anchor(self, anchor: NoteInfo) -> None:
        self._validate_joints(self._begin_info_with_anchor(anchor))

    def _to_node(self, anchor: NoteInfo, *, skip_validation: bool = False) -> Node:
        begin_info = self._begin_info_with_anchor(anchor)
        if not skip_validation:
            self._validate_joints(begin_info)
        action = Node(info=begin_info, _id=self._id)
        action.children = self._build_long_children(
            self._note_type,
            self._terminus_attr,
            begin_info,
            skip_validation=skip_validation,
        )
        air = Node(info=self._air_info_with_anchor(anchor), _id=self._air_id)
        air.children.append(action)
        return air

    def step(
        self,
        t: Tick,
        x: int,
        w: int,
        h: int,
    ) -> Self:
        self._add_step(t, x, w, h)
        return self

    def control(
        self,
        t: Tick,
        x: int,
        w: int,
        h: int,
    ) -> Self:
        self._add_control(t, x, w, h)
        return self

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

    @warnings.deprecated("CURVE_CONTROL is deprecated in Margrete.")
    def curve_control(
        self,
        t: Tick,
        x: int,
        w: int,
        h: int,
    ) -> Self:
        self._add_curve_control(t, x, w, h)
        return self

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

    def air(self, air: AirDirectionLike | Air | AirSlide | AirHold) -> Self:
        if isinstance(air, (AirDirection, str)):
            air = Air(air)
        if not isinstance(air, (Air, AirSlide, AirHold)):
            raise TypeError("air expects air direction, Air, AirSlide, or AirHold")
        self._air = air
        return self
