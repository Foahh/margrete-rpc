from __future__ import annotations

from ...chart_time import Tick, resolve_tick
from ..mg import MgNote
from ..types import AirCrushColor, AirCrushOption, LongAttr, NoteInfo, NoteType
from ._air import Air, AirHold, AirSlide, _AirAttachable
from ._joint import Joint, _JointHost
from ._shared import (
    _check_width,
    _coerce_aircrush_density_value,
    _copy_info,
    _GeometryInfoMixin,
    _HeightMixin,
    _info_property,
    _note_enum_line,
    _ShiftMixin,
)


class _PlaceableLong(_GeometryInfoMixin, _ShiftMixin, _JointHost):
    _note_type: NoteType

    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        _check_width(width)
        self._info = _copy_info(_info)
        self._id = _id
        self._joints: list[Joint] = []
        self._air: Air | AirSlide | AirHold | None = None
        self._info.type = self._note_type
        self._info.long_attr = LongAttr.BEGIN
        if _info is None:
            self._info.height = 800
        self.tick = tick
        self.x = x
        self.width = width

    @property
    def type(self) -> NoteType:
        return self._note_type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.BEGIN

    def _terminus_attr(self, joint: Joint) -> LongAttr:
        del joint
        return LongAttr.END

    def _to_mg_tree(self, *, skip_validation: bool = False) -> MgNote:
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
            f"tick={int(self.tick)}",
            f"x={self.x}",
            f"width={self.width}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if isinstance(self, AirCrush):
            parts.append(f"height={self.height}")
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

    def step(self, tick: Tick, *, x: int | None = None, width: int | None = None) -> Slide:
        self._add_step(tick, x=x, width=width)
        return self

    def control(self, tick: Tick, *, x: int | None = None, width: int | None = None) -> Slide:
        self._add_control(tick, x=x, width=width)
        return self

    def curve_control(self, tick: Tick, *, x: int | None = None, width: int | None = None) -> Slide:
        self._add_curve_control(tick, x=x, width=width)
        return self

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        return self._to_mg_tree(skip_validation=skip_validation)


class Hold(_AirAttachable, _PlaceableLong):
    _note_type = NoteType.HOLD

    def step(self, tick: Tick) -> Hold:
        tick = resolve_tick(tick)
        if self._joints:
            if int(tick) <= int(self._info.tick):
                raise ValueError("end tick must be later than the begin")
            self._joints[-1].tick = tick
        else:
            self._add_step(tick)
        return self

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        return self._to_mg_tree(skip_validation=skip_validation)


class AirCrush(_HeightMixin, _PlaceableLong):
    _note_type = NoteType.AIRCRUSH

    def __init__(
        self,
        tick: Tick,
        x: int,
        width: int,
        *,
        height: int,
        density: AirCrushOption | int,
        color: AirCrushColor = AirCrushColor.DEF,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, _info=_info, _id=_id)
        self.height = height
        self.density = density
        self.color = color

    @property
    def density(self) -> int:
        return int(self._info.option_value)

    @density.setter
    def density(self, value: object) -> None:
        self._info.option_value = _coerce_aircrush_density_value(value)

    color = _info_property("variation_id", AirCrushColor)

    def control(
        self,
        tick: Tick,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirCrush:
        self._add_control(tick, x=x, width=width, height=height)
        return self

    def to_mg(self, *, skip_validation: bool = False) -> MgNote:
        return self._to_mg_tree(skip_validation=skip_validation)
