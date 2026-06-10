from __future__ import annotations

from typing import Any, Self, cast

from ..constants import DEFAULT_H
from ..time import Position, resolve_density, resolve_tp
from .air import Air, AirHold, AirSlide, _AirAttachable
from .color import (
    ColorLike,
    ColorValue,
    color_to_value,
    color_value_from_proto,
)
from .joint import AirJoint, Joint, _AirJointHost, _JointHost, _JointHostBase
from .raw import RawNote
from .shared import (
    _check_air_matches,
    _check_tick,
    _check_width,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _note_enum_line,
    _TransformMixin,
)
from .types import LongAttr, NoteInfo, NoteType


def _coerce_aircrush_gap_value(value: object) -> int:
    if type(value) is int:
        return value
    if isinstance(value, tuple):
        return resolve_density(cast("tuple[int, int]", value))
    raise TypeError(
        f"gap must be int or (numerator, denominator) tuple, got {type(value).__name__}"
    )


class _PlaceableLong(_GeometryInfoMixin, _TransformMixin):
    _note_type: NoteType

    def __init__(
        self,
        *,
        t: int | None = None,
        p: Position | None = None,
        x: int,
        w: int,
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
            self._info.h = DEFAULT_H
        self.t = resolve_tp(t, p)
        self.x = x
        self.w = w

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        del joint
        return LongAttr.END

    def validate(self) -> None:
        _check_tick(self.t)
        _check_width(self.w)
        host = cast(_JointHostBase, self)
        host._validate_joints(self._info)
        if self._air is not None:
            self._air.validate()
            last = self._joints[-1]
            _check_air_matches(
                int(self._air.t), self._air.x, self._air.w, int(last.t), last.x, last.w
            )

    def _to_raw_tree(self, *, skip_validation: bool = False) -> RawNote:
        if not skip_validation:
            self.validate()
        host = cast(_JointHostBase, self)
        root = RawNote(info=self._info.copy(long_attr=LongAttr.BEGIN), _id=self._id)
        root.children = host._build_long_children(
            self._note_type,
            self._terminus_attr,
            root.info,
            skip_validation=skip_validation,
        )
        if self._air is not None:
            if not root.children:
                raise ValueError("attached air requires an end joint")
            root.children[-1].children.append(self._air.to_raw(skip_validation=skip_validation))
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
            parts.append(f"gap={self.gap}")
            parts.append(f"color={_note_enum_line(self.color)}")
        head = ", ".join(parts)
        lines = [f"{cls}({head}"]
        if self._joints:
            lines[0] += f", joints=[{', '.join(cast(_JointHostBase, self)._joint_strs())}]"
        lines[0] += ")"
        if self._air is not None:
            lines.extend(f"  {line}" for line in str(self._air).splitlines())
        return "\n".join(lines)

    __repr__ = __str__


class Slide(_AirAttachable, _PlaceableLong, _JointHost):
    _note_type = NoteType.SLIDE

    def with_step(self, *, t: int | None = None, p: Position | None = None, x: int, w: int) -> Self:
        copy = self.clone()
        copy.add_step(t=t, p=p, x=x, w=w)
        return copy

    def with_ctrl(self, *, t: int | None = None, p: Position | None = None, x: int, w: int) -> Self:
        copy = self.clone()
        copy.add_ctrl(t=t, p=p, x=x, w=w)
        return copy

    def converted[T: (AirSlide, AirCrush)](self, target: type[T], **overrides: Any) -> T:
        return cast(T, self._converted_to(target, **overrides))

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        return self._to_raw_tree(skip_validation=skip_validation)


class Hold(_AirAttachable, _PlaceableLong, _JointHost):
    _note_type = NoteType.HOLD

    def with_step(self, *, t: int | None = None, p: Position | None = None, x: int, w: int) -> Self:
        tick = resolve_tp(t, p)
        copy = self.clone()
        if copy._joints:
            if int(tick) <= int(copy._info.t):
                raise ValueError("end t must be later than the begin")
            joint = copy._joints[-1]
            joint.t = tick
            joint.x = x
            joint.w = w
        else:
            copy.add_step(t=tick, x=x, w=w)
        return copy

    def converted[T: (Slide, AirSlide, AirCrush, AirHold)](
        self, target: type[T], **overrides: Any
    ) -> T:
        return cast(T, self._converted_to(target, **overrides))

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        return self._to_raw_tree(skip_validation=skip_validation)


class AirCrush(_HeightMixin, _PlaceableLong, _AirJointHost):
    _note_type = NoteType.AIRCRUSH
    _joint_type = AirJoint

    def __init__(
        self,
        *,
        t: int | None = None,
        p: Position | None = None,
        x: int,
        w: int,
        h: int,
        gap: int,
        color: ColorLike | int = ColorValue.DEFAULT,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(t=t, p=p, x=x, w=w, _info=_info, _id=_id)
        self.h = h
        self.gap = gap
        self.color = color

    @property
    def gap(self) -> int:
        return int(self._info.option_value)

    @gap.setter
    def gap(self, value: object) -> None:
        self._info.option_value = _coerce_aircrush_gap_value(value)

    @property
    def color(self) -> ColorValue | int:
        return color_value_from_proto(int(self._info.variation_id))

    @color.setter
    def color(self, value: ColorLike | int) -> None:
        self._info.variation_id = color_to_value(value)

    def with_ctrl(
        self, *, t: int | None = None, p: Position | None = None, x: int, w: int, h: int
    ) -> Self:
        copy = self.clone()
        copy.add_ctrl(t=t, p=p, x=x, w=w, h=h)
        return copy

    def converted[T: (Slide, AirSlide)](self, target: type[T], **overrides: Any) -> T:
        return cast(T, self._converted_to(target, **overrides))

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        return self._to_raw_tree(skip_validation=skip_validation)
