from __future__ import annotations

from margrete_rpc._warnings import warnings

from ..time import Tick, resolve_tick
from .air import Air, AirHold, AirSlide, _AirAttachable
from .color import (
    ColorLike,
    ColorValue,
    color_to_value,
    color_value_from_proto,
)
from .joint import AirJoint, Joint, _JointHost
from .node import Node
from .shared import (
    _check_tick,
    _check_width,
    _coerce_aircrush_density_value,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _note_enum_line,
    _TransformMixin,
)
from .types import LongAttr, NoteInfo, NoteType


class _PlaceableLong(_GeometryInfoMixin, _TransformMixin, _JointHost):
    _note_type: NoteType

    def __init__(
        self,
        t: Tick,
        x: int,
        w: int,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        _check_width(w)
        self._info = _copy_info(_info)
        self._id = _id
        self._joints: list[Joint] = []
        self._air: Air | AirSlide | AirHold | None = None
        self._info.type = self._note_type
        self._info.long_attr = LongAttr.BEGIN
        if _info is None:
            self._info.h = 800
        self.t = t
        self.x = x
        self.w = w

    @property
    def type(self) -> NoteType:
        return self._note_type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.BEGIN

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        del joint
        return LongAttr.END

    def validate(self) -> None:
        _check_tick(self.t)
        _check_width(self.w)
        self._validate_joints(self._info)
        if self._air is not None:
            children = self._build_long_children(
                self._note_type,
                self._terminus_attr,
                self._info,
                skip_validation=True,
            )
            self._air._validate_with_anchor(children[-1].info)

    def _to_node_tree(self, *, skip_validation: bool = False) -> Node:
        if not skip_validation:
            self.validate()
        root = Node(info=self._info.copy(long_attr=LongAttr.BEGIN), _id=self._id)
        root.children = self._build_long_children(
            self._note_type,
            self._terminus_attr,
            root.info,
            skip_validation=skip_validation,
        )
        if self._air is not None:
            if not root.children:
                raise ValueError("attached air requires an end joint")
            root.children[-1].children.append(
                self._air._to_node(root.children[-1].info, skip_validation=skip_validation)
            )
        return root

    def __str__(self) -> str:
        cls = self.__class__.__name__
        parts = [
            f"t={int(self.t)}",
            f"x={self.x}",
            f"w={self.w}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if isinstance(self, AirCrush):
            parts.append(f"h={self.h}")
            parts.append(f"density={self.density}")
            parts.append(f"color={_note_enum_line(self.color)}")
        head = ", ".join(parts)
        lines = [f"{cls}({head}"]
        if self._joints:
            lines[0] += f", joints=[{', '.join(self._joint_strs())}]"
        lines[0] += ")"
        if self._air is not None:
            lines.extend(f"  {line}" for line in str(self._air).splitlines())
        return "\n".join(lines)

    __repr__ = __str__


class Slide(_AirAttachable, _PlaceableLong):
    _note_type = NoteType.SLIDE

    def step(
        self,
        t: Tick,
        x: int,
        w: int,
    ) -> Slide:
        self._add_step(t, x, w, 800)
        return self

    def control(
        self,
        t: Tick,
        x: int,
        w: int,
    ) -> Slide:
        self._add_control(t, x, w, 800)
        return self

    @warnings.deprecated("CURVE_CONTROL is deprecated in Margrete.")
    def curve_control(
        self,
        t: Tick,
        x: int,
        w: int,
    ) -> Slide:
        self._add_curve_control(t, x, w, 800)
        return self

    def to_node(self, *, skip_validation: bool = False) -> Node:
        return self._to_node_tree(skip_validation=skip_validation)


class Hold(_AirAttachable, _PlaceableLong):
    _note_type = NoteType.HOLD

    def step(self, t: Tick, x: int, w: int) -> Hold:
        t = resolve_tick(t)
        if self._joints:
            if int(t) <= int(self._info.t):
                raise ValueError("end t must be later than the begin")
            joint = self._joints[-1]
            joint.t = t
            joint.x = x
            joint.w = w
        else:
            self._add_step(t, x, w, 800)
        return self

    def to_node(self, *, skip_validation: bool = False) -> Node:
        return self._to_node_tree(skip_validation=skip_validation)


class AirCrush(_HeightMixin, _PlaceableLong):
    _note_type = NoteType.AIRCRUSH
    _joint_type = AirJoint

    def __init__(
        self,
        t: Tick,
        x: int,
        w: int,
        *,
        h: int,
        density: int,
        color: ColorLike | int = ColorValue.DEFAULT,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(t, x, w, _info=_info, _id=_id)
        self.h = h
        self.density = density
        self.color = color

    @property
    def density(self) -> int:
        return int(self._info.option_value)

    @density.setter
    def density(self, value: object) -> None:
        self._info.option_value = _coerce_aircrush_density_value(value)

    @property
    def color(self) -> ColorValue | int:
        return color_value_from_proto(int(self._info.variation_id))

    @color.setter
    def color(self, value: ColorLike | int) -> None:
        self._info.variation_id = color_to_value(value)

    def control(
        self,
        t: Tick,
        x: int,
        w: int,
        h: int,
    ) -> AirCrush:
        self._add_control(t, x, w, h)
        return self

    def to_node(self, *, skip_validation: bool = False) -> Node:
        return self._to_node_tree(skip_validation=skip_validation)
