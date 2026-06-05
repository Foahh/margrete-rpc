from __future__ import annotations

from collections.abc import Callable

from ..time import Tick
from ._shared import (
    _check_tick,
    _check_width,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _info_property,
    _note_enum_line,
)
from .node import Node
from .types import LongAttr, NoteInfo, NoteType


class Joint(_GeometryInfoMixin, _HeightMixin):
    kind = _info_property("long_attr", LongAttr)

    @property
    def info(self) -> NoteInfo:
        return self._info

    @info.setter
    def info(self, value: NoteInfo) -> None:
        self._info = value

    def __init__(
        self,
        t: Tick,
        x: int,
        w: int,
        h: int = 800,
        info: NoteInfo | None = None,
        _id: int | None = None,
        *,
        kind: LongAttr,
        default_x: bool = False,
        default_width: bool = False,
        default_height: bool = False,
    ) -> None:
        self.info = _copy_info(info)
        self._id = _id
        self._default_x = default_x
        self._default_width = default_width
        self._default_height = default_height
        self.t = t
        self._info.x = x
        self._info.w = w
        self._info.h = h
        self.kind = kind
        if not default_width:
            _check_width(w)


class _JointHost:
    _joints: list[Joint]

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

    def _joint_geometry(
        self,
        *,
        x: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> tuple[int, int, int, bool, bool, bool]:
        previous = self._joints[-1] if self._joints else self._begin_info_for_defaults()
        default_x = x is None
        default_width = w is None
        default_height = h is None
        previous_w = previous.w
        previous_h = previous.h
        return (
            previous.x if x is None else x,
            previous_w if w is None else w,
            previous_h if h is None else h,
            default_x,
            default_width,
            default_height,
        )

    def _make_joint(
        self,
        t: Tick,
        long_attr: LongAttr,
        *,
        x: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> Joint:
        (
            joint_x,
            joint_width,
            joint_height,
            default_x,
            default_width,
            default_height,
        ) = self._joint_geometry(x=x, w=w, h=h)
        return Joint(
            t=t,
            x=joint_x,
            w=joint_width,
            h=joint_height,
            kind=long_attr,
            default_x=default_x,
            default_width=default_width,
            default_height=default_height,
        )

    def _add_joint(self, joint: Joint) -> None:
        _check_tick(joint.t)
        if not joint._default_width:
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
            if not isinstance(joint, Joint):
                raise TypeError(f"joint at index {index} must be Joint")
            _check_tick(joint.t)
            if not joint._default_width:
                _check_width(joint.w)
            if int(joint.t) <= previous_tick:
                raise ValueError("joint t must be later than previous joint")
            previous_tick = int(joint.t)

        if self._joints[-1].kind not in (LongAttr.STEP, LongAttr.CONTROL):
            raise ValueError("long note must end with a step or control joint")

    def _add_step(
        self,
        t: Tick,
        *,
        x: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        self._add_joint(
            self._make_joint(
                t,
                LongAttr.STEP,
                x=x,
                w=w,
                h=h,
            )
        )

    def _add_control(
        self,
        t: Tick,
        *,
        x: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        self._add_joint(
            self._make_joint(
                t,
                LongAttr.CONTROL,
                x=x,
                w=w,
                h=h,
            )
        )

    def _add_curve_control(
        self,
        t: Tick,
        *,
        x: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        self._add_joint(
            self._make_joint(
                t,
                LongAttr.CURVE_CONTROL,
                x=x,
                w=w,
                h=h,
            )
        )

    def _resolve_joint_info(
        self,
        joint: Joint,
        previous: NoteInfo,
        note_type: NoteType,
        long_attr: LongAttr,
    ) -> NoteInfo:
        return joint.info.copy(
            type=note_type,
            long_attr=long_attr,
            x=previous.x if joint._default_x else joint.x,
            w=previous.w if joint._default_width else joint.w,
            h=previous.h if joint._default_height else joint.h,
        )

    def _build_long_children(
        self,
        note_type: NoteType,
        terminus_attr: Callable[[Joint], LongAttr],
        begin_info: NoteInfo,
        *,
        skip_validation: bool = False,
    ) -> list[Node]:
        if not skip_validation:
            self._validate_joints(begin_info)

        children: list[Node] = []
        previous = begin_info
        for index, joint in enumerate(self._joints):
            long_attr = joint.kind
            if not skip_validation and index == len(self._joints) - 1:
                long_attr = terminus_attr(joint)
            jinfo = self._resolve_joint_info(joint, previous, note_type, long_attr)
            if note_type is NoteType.AIRCRUSH:
                jinfo = jinfo.copy(option_value=0)
            children.append(Node(info=jinfo, _id=joint._id))
            previous = jinfo
        return children

    def _joint_strs(self) -> list[str]:
        joint_strs: list[str] = []
        for j in self._joints:
            jbits = [
                f"t={int(j.t)}",
                f"kind={_note_enum_line(j.kind)}",
                f"x={j.x}",
                f"w={j.w}",
                f"h={j.h}",
            ]
            if j.info.option_value != 0:
                jbits.append(f"option_value={j.info.option_value}")
            joint_strs.append(f"Joint({', '.join(jbits)})")
        return joint_strs
