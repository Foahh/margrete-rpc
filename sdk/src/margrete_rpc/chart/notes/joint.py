from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, Self

from ..constants import DEFAULT_H
from ..time import Position, resolve_tp
from .raw import RawNote
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
    """A waypoint in a ground long note (:class:`Hold` / :class:`Slide`).

    A joint has timing and lane geometry plus a :attr:`kind` (step, control, or curve
    control) that determines how the long note's shape passes through it.
    """

    def __init__(
        self,
        *,
        t: int | None = None,
        p: Position | None = None,
        x: int,
        w: int,
        _id: int | None = None,
        kind: JointKindLike,
    ) -> None:
        """Create a joint.

        Args:
            t: Absolute tick (mutually exclusive with ``p``).
            p: A :data:`Position` (mutually exclusive with ``t``).
            x: Left lane index.
            w: Width in lane units.
            kind: Joint kind (:class:`JointKind` or its string form).
        """
        self._info = _copy_info(None)
        self._id = _id
        self._kind = JointKind.STEP
        self.t = resolve_tp(t, p)
        self._info.x = x
        self._info.w = w
        self._info.h = DEFAULT_H
        self.kind = kind
        _check_width(w)

    @property
    def kind(self) -> JointKind:
        """The joint's kind (:class:`JointKind`)."""
        return self._kind

    @kind.setter
    def kind(self, value: JointKindLike) -> None:
        self._kind = JointKind(value)


class AirJoint(Joint, _HeightMixin):
    """A :class:`Joint` for air long notes, additionally carrying height ``h``."""

    def __init__(
        self,
        *,
        t: int | None = None,
        p: Position | None = None,
        x: int,
        w: int,
        h: int,
        _id: int | None = None,
        kind: JointKindLike,
    ) -> None:
        """Create an air joint. As :class:`Joint`, plus ``h`` for the joint's air height."""
        super().__init__(t=t, p=p, x=x, w=w, _id=_id, kind=kind)
        self.h = h


class _JointHostBase:
    _joints: list[Joint]
    _joint_type: ClassVar[type[Joint]] = Joint
    _info: NoteInfo

    @property
    def joints(self) -> list[Joint]:
        """The long note's joints, in order from first to last."""
        return self._joints

    @property
    def duration(self) -> int:
        """Ticks from the begin to the last joint (0 if there are no joints)."""
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
        t: int,
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

    def add_step(self, *, t: int | None = None, p: Position | None = None, x: int, w: int) -> Self:
        """Append a step joint in place and return ``self``. Timing must be strictly
        increasing along the note."""
        self._add_joint(self._make_joint(resolve_tp(t, p), JointKind.STEP, x, w))
        return self

    def add_ctrl(self, *, t: int | None = None, p: Position | None = None, x: int, w: int) -> Self:
        """Append a control joint in place and return ``self``. Timing must be strictly
        increasing along the note."""
        self._add_joint(self._make_joint(resolve_tp(t, p), JointKind.CONTROL, x, w))
        return self

    def _add_curve_control(
        self, *, t: int | None = None, p: Position | None = None, x: int, w: int
    ) -> None:
        self._add_joint(self._make_joint(resolve_tp(t, p), JointKind.CURVE_CONTROL, x, w))


class _AirJointHost(_JointHostBase):
    _joint_type: ClassVar[type[Joint]] = AirJoint

    def _make_joint(
        self,
        t: int,
        kind: JointKind,
        x: int,
        w: int,
        h: int,
    ) -> AirJoint:
        return AirJoint(t=t, x=x, w=w, h=h, kind=kind)

    def add_step(
        self, *, t: int | None = None, p: Position | None = None, x: int, w: int, h: int
    ) -> Self:
        """Append a step joint (with air height ``h``) in place and return ``self``."""
        self._add_joint(self._make_joint(resolve_tp(t, p), JointKind.STEP, x, w, h))
        return self

    def add_ctrl(
        self, *, t: int | None = None, p: Position | None = None, x: int, w: int, h: int
    ) -> Self:
        """Append a control joint (with air height ``h``) in place and return ``self``."""
        self._add_joint(self._make_joint(resolve_tp(t, p), JointKind.CONTROL, x, w, h))
        return self

    def _add_curve_control(
        self, *, t: int | None = None, p: Position | None = None, x: int, w: int, h: int
    ) -> None:
        self._add_joint(self._make_joint(resolve_tp(t, p), JointKind.CURVE_CONTROL, x, w, h))


__all__ = ["AirJoint", "Joint", "_AirJointHost", "_JointHost", "_JointHostBase"]
