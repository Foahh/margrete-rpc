from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, Self

from ..raw import RawNote
from ..time import Tick
from .shared import (
    _check_tick,
    _check_width,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _note_enum_line,
)
from .types import (
    JointKind,
    JointKindLike,
    LongAttr,
    NoteInfo,
    NoteType,
    joint_kind_to_long_attr,
)


class Joint(_GeometryInfoMixin):
    def __init__(
        self,
        *,
        t: Tick,
        x: int,
        w: int,
        _id: int | None = None,
        kind: JointKindLike,
    ) -> None:
        self._info = _copy_info(None)
        self._id = _id
        self._kind = JointKind.STEP
        self.t = t
        self._info.x = x
        self._info.w = w
        self._info.h = 80
        self.kind = kind
        _check_width(w)

    @property
    def kind(self) -> JointKind:
        return self._kind

    @kind.setter
    def kind(self, value: JointKindLike) -> None:
        self._kind = JointKind(value)


class AirJoint(Joint, _HeightMixin):
    def __init__(
        self,
        *,
        t: Tick,
        x: int,
        w: int,
        h: int,
        _id: int | None = None,
        kind: JointKindLike,
    ) -> None:
        super().__init__(t=t, x=x, w=w, _id=_id, kind=kind)
        self.h = h


class _JointHostBase:
    _joints: list[Joint]
    _joint_type: ClassVar[type[Joint]] = Joint

    @property
    def joints(self) -> list[Joint]:
        return self._joints

    @property
    def duration(self) -> int:
        if not self._joints:
            return 0
        return int(self._joints[-1].t) - int(self._begin_info_for_defaults().t)

    def _begin_info_for_defaults(self) -> NoteInfo:
        return self._info

    def _add_joint(self, joint: Joint) -> None:
        if type(joint) is not self._joint_type:
            raise TypeError(f"joint must be {self._joint_type.__name__}")
        _check_tick(joint.t)
        _check_width(joint.w)
        previous_tick = int(
            self._joints[-1].t if self._joints else self._begin_info_for_defaults().t
        )
        if int(joint.t) <= previous_tick:
            raise ValueError("joint t must be later than previous joint")
        self._joints.append(joint)

    def validate(self) -> None:
        self._validate_joints(self._begin_info_for_defaults())

    def _validate_joints(self, begin_info: NoteInfo) -> None:
        if not self._joints:
            raise ValueError("long note requires at least one joint")

        previous_tick = int(begin_info.t)
        for index, joint in enumerate(self._joints):
            if type(joint) is not self._joint_type:
                raise TypeError(f"joint at index {index} must be {self._joint_type.__name__}")
            _check_tick(joint.t)
            _check_width(joint.w)
            if int(joint.t) <= previous_tick:
                raise ValueError("joint t must be later than previous joint")
            previous_tick = int(joint.t)

        if self._joints[-1].kind not in (JointKind.STEP, JointKind.CONTROL):
            raise ValueError("long note must end with a step or control joint")

    def _resolve_joint_info(
        self,
        joint: Joint,
        note_type: NoteType,
        long_attr: LongAttr,
    ) -> NoteInfo:
        return joint._info.copy(
            type=note_type,
            long_attr=long_attr,
        )

    def _build_long_children(
        self,
        note_type: NoteType,
        terminus_attr: Callable[[Joint], LongAttr],
        begin_info: NoteInfo,
        *,
        skip_validation: bool = False,
    ) -> list[RawNote]:
        if not skip_validation:
            self._validate_joints(begin_info)

        children: list[RawNote] = []
        for index, joint in enumerate(self._joints):
            long_attr = joint_kind_to_long_attr(joint.kind)
            if not skip_validation and index == len(self._joints) - 1:
                long_attr = terminus_attr(joint)
            jinfo = self._resolve_joint_info(joint, note_type, long_attr)
            if note_type is NoteType.AIRCRUSH:
                jinfo = jinfo.copy(option_value=0)
            children.append(RawNote(info=jinfo, _id=joint._id))
        return children

    def _joint_strs(self) -> list[str]:
        joint_strs: list[str] = []
        for j in self._joints:
            jbits = [
                f"t={int(j.t)}",
                f"kind={_note_enum_line(j.kind)}",
                f"x={j.x}",
                f"w={j.w}",
            ]
            if isinstance(j, AirJoint):
                jbits.append(f"h={j.h}")
            if j._info.option_value != 0:
                jbits.append(f"option_value={j._info.option_value}")
            joint_strs.append(f"{j.__class__.__name__}({', '.join(jbits)})")
        return joint_strs


class _JointHost(_JointHostBase):
    def _make_joint(
        self,
        t: Tick,
        kind: JointKind,
        x: int,
        w: int,
    ) -> Joint:
        return self._joint_type(
            t=t,
            x=x,
            w=w,
            kind=kind,
        )

    def add_step(self, *, t: Tick, x: int, w: int) -> Self:
        self._add_joint(self._make_joint(t, JointKind.STEP, x, w))
        return self

    def add_ctrl(self, *, t: Tick, x: int, w: int) -> Self:
        self._add_joint(self._make_joint(t, JointKind.CONTROL, x, w))
        return self

    def _add_curve_control(self, *, t: Tick, x: int, w: int) -> None:
        self._add_joint(self._make_joint(t, JointKind.CURVE_CONTROL, x, w))


class _AirJointHost(_JointHostBase):
    _joint_type: ClassVar[type[Joint]] = AirJoint

    def _make_joint(
        self,
        t: Tick,
        kind: JointKind,
        x: int,
        w: int,
        h: int,
    ) -> AirJoint:
        return AirJoint(t=t, x=x, w=w, h=h, kind=kind)

    def add_step(self, *, t: Tick, x: int, w: int, h: int) -> Self:
        self._add_joint(self._make_joint(t, JointKind.STEP, x, w, h))
        return self

    def add_ctrl(self, *, t: Tick, x: int, w: int, h: int) -> Self:
        self._add_joint(self._make_joint(t, JointKind.CONTROL, x, w, h))
        return self

    def _add_curve_control(self, *, t: Tick, x: int, w: int, h: int) -> None:
        self._add_joint(self._make_joint(t, JointKind.CURVE_CONTROL, x, w, h))


__all__ = ["AirJoint", "Joint", "_AirJointHost", "_JointHost", "_JointHostBase"]
