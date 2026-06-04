from __future__ import annotations

from typing import Self

from ...chart_time import Tick
from ..mg import MgNote
from ..types import AirDirection, ExAttr, LongAttr, NoteInfo, NoteType
from ._joint import Joint, _JointHost
from ._shared import (
    _copy_info,
    _direction_property,
    _HeightMixin,
    _info_property,
    _note_enum_line,
)


class Air:
    direction = _direction_property(AirDirection, "air")
    til = _info_property("timeline_id")

    def __init__(
        self,
        direction: AirDirection,
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

    def _to_mg(self, anchor: NoteInfo, *, skip_validation: bool = False) -> MgNote:
        del skip_validation
        return MgNote(
            info=self._info.copy(
                type=NoteType.AIR,
                long_attr=LongAttr.NONE,
                tick=anchor.tick,
                x=anchor.x,
                width=anchor.width,
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

    def __init__(
        self,
        *,
        height: int,
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
            self._air_info.height = height
        if _info is None:
            self._info.height = height
        else:
            self.height = height

    def _begin_info_for_defaults(self) -> NoteInfo:
        return self._info

    @property
    def type(self) -> NoteType:
        return self._note_type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.BEGIN

    def _air_info_with_anchor(self, anchor: NoteInfo) -> NoteInfo:
        return self._air_info.copy(tick=anchor.tick, x=anchor.x, width=anchor.width)

    def _begin_info_with_anchor(self, anchor: NoteInfo) -> NoteInfo:
        return self._info.copy(tick=anchor.tick, x=anchor.x, width=anchor.width)

    def _to_mg(self, anchor: NoteInfo, *, skip_validation: bool = False) -> MgNote:
        begin_info = self._begin_info_with_anchor(anchor)
        action = MgNote(info=begin_info, _id=self._id)
        action.children = self._build_long_children(
            self._note_type,
            self._terminus_attr,
            begin_info,
            skip_validation=skip_validation,
        )
        air = MgNote(info=self._air_info_with_anchor(anchor), _id=self._air_id)
        air.children.append(action)
        return air

    def step(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> Self:
        self._add_step(tick, x=x, width=width, height=height)
        return self

    def control(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> Self:
        self._add_control(tick, x=x, width=width, height=height)
        return self

    def __str__(self) -> str:
        parts = [f"height={self.height}"]
        if self._id is not None:
            parts.append(f"id={self._id}")
        head = ", ".join(parts)
        if not self._joints:
            return f"{self.__class__.__name__}({head})"
        return f"{self.__class__.__name__}({head}, joints=[{', '.join(self._joint_strs())}])"

    __repr__ = __str__


class AirSlide(_AttachableAirLong):
    _note_type = NoteType.AIRSLIDE

    def curve_control(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> Self:
        self._add_curve_control(tick, x=x, width=width, height=height)
        return self

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        if joint.long_attr is LongAttr.CONTROL:
            return LongAttr.END_NOACT
        return LongAttr.END


class AirHold(_AttachableAirLong):
    _note_type = NoteType.AIRHOLD

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        if joint.long_attr is LongAttr.CONTROL:
            return LongAttr.END_NOACT
        return LongAttr.END


class _AirAttachable:
    _air: Air | AirSlide | AirHold | None

    def air(self, air: AirDirection | Air | AirSlide | AirHold) -> Self:
        if isinstance(air, AirDirection):
            air = Air(air)
        if not isinstance(air, (Air, AirSlide, AirHold)):
            raise TypeError("air expects AirDirection, Air, AirSlide, or AirHold")
        self._air = air
        return self
