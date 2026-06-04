from __future__ import annotations

from collections.abc import Callable

from ...chart_time import Tick
from ..ll import LLNote
from ..types import LongAttr, NoteInfo, NoteType
from ._shared import (
    _check_tick,
    _check_width,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _hl_enum_line,
    _info_property,
)


class Joint(_GeometryInfoMixin, _HeightMixin):
    long_attr = _info_property("long_attr", LongAttr)

    @property
    def info(self) -> NoteInfo:
        return self._info

    @info.setter
    def info(self, value: NoteInfo) -> None:
        self._info = value

    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        long_attr: LongAttr,
        height: int = 800,
        info: NoteInfo | None = None,
        _id: int | None = None,
        *,
        default_x: bool = False,
        default_width: bool = False,
        default_height: bool = False,
    ) -> None:
        self.info = _copy_info(info)
        self._id = _id
        self._default_x = default_x
        self._default_width = default_width
        self._default_height = default_height
        self.tick = tick
        self._info.x = x
        self._info.width = width
        self._info.height = height
        self.long_attr = long_attr
        if not default_width:
            _check_width(width)


class _JointHost:
    _joints: list[Joint]

    @property
    def joints(self) -> list[Joint]:
        return self._joints

    @property
    def duration(self) -> int:
        if not self._joints:
            return 0
        return int(self._joints[-1].tick) - int(self._begin_info_for_defaults().tick)

    def _begin_info_for_defaults(self) -> NoteInfo:
        return self._info

    def _joint_geometry(
        self,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[int, int, int, bool, bool, bool]:
        previous = self._joints[-1] if self._joints else self._begin_info_for_defaults()
        default_x = x is None
        default_width = width is None
        default_height = height is None
        return (
            previous.x if x is None else x,
            previous.width if width is None else width,
            previous.height if height is None else height,
            default_x,
            default_width,
            default_height,
        )

    def _make_joint(
        self,
        tick: Tick,
        long_attr: LongAttr,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> Joint:
        (
            joint_x,
            joint_width,
            joint_height,
            default_x,
            default_width,
            default_height,
        ) = self._joint_geometry(x=x, width=width, height=height)
        return Joint(
            tick=tick,
            x=joint_x,
            width=joint_width,
            height=joint_height,
            long_attr=long_attr,
            default_x=default_x,
            default_width=default_width,
            default_height=default_height,
        )

    def _add_joint(self, joint: Joint) -> None:
        _check_tick(joint.tick)
        if not joint._default_width:
            _check_width(joint.width)
        previous_tick = int(
            self._joints[-1].tick if self._joints else self._begin_info_for_defaults().tick
        )
        if int(joint.tick) <= previous_tick:
            raise ValueError("joint tick must be later than previous joint")
        self._joints.append(joint)

    def _add_step(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        self._add_joint(self._make_joint(tick, LongAttr.STEP, x=x, width=width, height=height))

    def _add_control(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        self._add_joint(self._make_joint(tick, LongAttr.CONTROL, x=x, width=width, height=height))

    def _add_curve_control(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        self._add_joint(
            self._make_joint(
                tick,
                LongAttr.CURVE_CONTROL,
                x=x,
                width=width,
                height=height,
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
            width=previous.width if joint._default_width else joint.width,
            height=previous.height if joint._default_height else joint.height,
        )

    def _build_long_children(
        self,
        note_type: NoteType,
        terminus_attr: Callable[[Joint], LongAttr],
        begin_info: NoteInfo,
        *,
        skip_validation: bool = False,
    ) -> list[LLNote]:
        if not skip_validation:
            if not self._joints:
                raise ValueError("long note requires at least one joint")
            if self._joints[-1].long_attr not in (LongAttr.STEP, LongAttr.CONTROL):
                raise ValueError("long note must end with a step or control joint")

        children: list[LLNote] = []
        previous = begin_info
        for index, joint in enumerate(self._joints):
            long_attr = joint.long_attr
            if not skip_validation and index == len(self._joints) - 1:
                long_attr = terminus_attr(joint)
            jinfo = self._resolve_joint_info(joint, previous, note_type, long_attr)
            if note_type is NoteType.AIRCRUSH:
                jinfo = jinfo.copy(option_value=0)
            children.append(LLNote(info=jinfo, _id=joint._id))
            previous = jinfo
        return children

    def _joint_strs(self) -> list[str]:
        joint_strs: list[str] = []
        for j in self._joints:
            jbits = [
                f"tick={int(j.tick)}",
                f"long_attr={_hl_enum_line(j.long_attr)}",
                f"x={j.x}",
                f"width={j.width}",
                f"height={j.height}",
            ]
            if j.info.option_value != 0:
                jbits.append(f"option_value={j.info.option_value}")
            joint_strs.append(f"Joint({', '.join(jbits)})")
        return joint_strs
