from __future__ import annotations

from ..time import Tick, resolve_tick
from .color import (
    AirCrushColor,
    AirCrushColorLike,
    air_crush_color_from_value,
    air_crush_color_to_value,
)
from .mg import MgNote
from .types import LongAttr, NoteInfo, NoteType
from ._air import Air, AirHold, AirSlide, _AirAttachable
from ._joint import Joint, _JointHost
from ._shared import (
    _check_tick,
    _check_width,
    _coerce_aircrush_density_value,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _note_enum_line,
    _ShiftMixin,
)


class _PlaceableLong(_GeometryInfoMixin, _ShiftMixin, _JointHost):
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

    def _to_mg_tree(self, *, skip_validation: bool = False) -> MgNote:
        if not skip_validation:
            self.validate()
        root = MgNote(info=self._info.copy(long_attr=LongAttr.BEGIN), _id=self._id)
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
                self._air._to_mg(root.children[-1].info, skip_validation=skip_validation)
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
        *,
        x: int | None = None,
        w: int | None = None,
    ) -> Slide:
        self._add_step(t, x=x, w=w)
        return self

    def control(
        self,
        t: Tick,
        *,
        x: int | None = None,
        w: int | None = None,
    ) -> Slide:
        self._add_control(t, x=x, w=w)
        return self

    def curve_control(
        self,
        t: Tick,
        *,
        x: int | None = None,
        w: int | None = None,
    ) -> Slide:
        self._add_curve_control(t, x=x, w=w)
        return self

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        return self._to_mg_tree(skip_validation=skip_validation)


class Hold(_AirAttachable, _PlaceableLong):
    _note_type = NoteType.HOLD

    def step(self, t: Tick) -> Hold:
        t = resolve_tick(t)
        if self._joints:
            if int(t) <= int(self._info.t):
                raise ValueError("end t must be later than the begin")
            self._joints[-1].t = t
        else:
            self._add_step(t)
        return self

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        return self._to_mg_tree(skip_validation=skip_validation)


class AirCrush(_HeightMixin, _PlaceableLong):
    _note_type = NoteType.AIRCRUSH

    def __init__(
        self,
        t: Tick,
        x: int,
        w: int,
        *,
        h: int,
        density: int,
        color: AirCrushColorLike | int = AirCrushColor.DEFAULT,
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
    def color(self) -> AirCrushColor | int:
        return air_crush_color_from_value(air_crush_color_to_value(self._info.variation_id))

    @color.setter
    def color(self, value: AirCrushColorLike | int) -> None:
        self._info.variation_id = air_crush_color_from_value(air_crush_color_to_value(value))

    def control(
        self,
        t: Tick,
        *,
        x: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> AirCrush:
        self._add_control(t, x=x, w=w, h=h)
        return self

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        return self._to_mg_tree(skip_validation=skip_validation)
