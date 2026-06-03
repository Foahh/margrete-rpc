from __future__ import annotations

from enum import IntEnum
from typing import Any, Protocol, Self, cast, runtime_checkable

from .ll import LLNote
from .types import (
    AirCrushColor,
    AirCrushOption,
    AirDirection,
    ExAttr,
    ExtapDirection,
    FlickDirection,
    LongAttr,
    NoteInfo,
    NoteType,
)


class UnsupportedNoteTree(ValueError):
    pass


@runtime_checkable
class HLNote(Protocol):
    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        raise NotImplementedError

    def shift(self, *, t: int = 0, x: int = 0, w: int = 0, h: int = 0) -> Self: ...


def _hl_enum_line(value: IntEnum | int) -> str:
    if isinstance(value, IntEnum):
        return f"{type(value).__name__}.{value.name}({int(value)})"
    return repr(value)


def _check_tick(tick: int) -> None:
    if int(tick) < 0:
        raise ValueError("tick must be non-negative")


def _check_width(width: int) -> None:
    if width < 1:
        raise ValueError("width must be at least 1")


def _copy_info(info: NoteInfo | None) -> NoteInfo:
    return info.copy() if info is not None else NoteInfo()


def _stored_value(value: Any) -> Any:
    return int(value) if isinstance(value, IntEnum) else value


def _enum_value(enum_type: type[IntEnum], value: int) -> IntEnum | int:
    try:
        return enum_type(value)
    except ValueError:
        return value


def _info_value(value: Any, enum_type: type[IntEnum] | None) -> Any:
    if enum_type is None:
        return _stored_value(value)
    try:
        return enum_type(value)
    except ValueError:
        return _stored_value(value)


def _info_property(name: str, enum_type: type[IntEnum] | None = None):
    def getter(self):
        value = getattr(self._info, name)
        return _enum_value(enum_type, value) if enum_type is not None else value

    def setter(self, value):
        setattr(self._info, name, _info_value(value, enum_type))

    return property(getter, setter)


def _checked_info_property(name: str, check):
    def getter(self):
        return getattr(self._info, name)

    def setter(self, value):
        check(value)
        setattr(self._info, name, value)

    return property(getter, setter)


def _direction_property(enum_type: type[IntEnum], label: str):
    def getter(self):
        return enum_type(int(self._info.direction))

    def setter(self, value):
        try:
            direction = enum_type(int(value))
        except ValueError as exc:
            raise ValueError(f"invalid {label} direction") from exc
        self._info.direction = direction

    return property(getter, setter)


def _coerce_aircrush_density_value(value: object) -> int:
    if isinstance(value, AirCrushOption):
        return int(value)
    if type(value) is int:
        return value
    raise TypeError(f"density must be int or AirCrushOption, got {type(value).__name__}")


class _GeometryInfoMixin:
    tick = _checked_info_property("tick", _check_tick)
    x = _info_property("x")
    width = _checked_info_property("width", _check_width)
    til = _info_property("timeline_id")


class _ShiftMixin:
    def shift(self, *, t: int = 0, x: int = 0, w: int = 0, h: int = 0) -> Self:
        from .shift import _shift_hl

        return _shift_hl(self, t=t, x=x, w=w, h=h)


class Air(_GeometryInfoMixin, _ShiftMixin):
    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        direction: AirDirection,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._info = _copy_info(_info)
        self._id = _id
        self._parent_id: int | None = None
        self._long_action: object | None = None
        self._info.type = NoteType.AIR
        self._info.long_attr = LongAttr.NONE
        self.tick = tick
        self.x = x
        self.width = width
        self.direction = direction

    direction = _direction_property(AirDirection, "air")
    height = _info_property("height")

    @property
    def inverted(self) -> bool:
        return self._info.ex_attr == ExAttr.INVERT

    @inverted.setter
    def inverted(self, value: bool) -> None:
        self._info.ex_attr = ExAttr.INVERT if value else ExAttr.NONE

    def __post_init__(self) -> None:
        _check_tick(self.tick)
        _check_width(self.width)

    @property
    def type(self) -> NoteType:
        return NoteType.AIR

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.NONE

    def _attach_to(self, parent: object) -> None:
        parent_id = id(parent)
        if self._parent_id is not None and self._parent_id != parent_id:
            raise ValueError("one air object cannot attach to many ground notes")
        self._parent_id = parent_id

    def slide(self, *, height: int) -> AirSlide:
        if self._long_action is not None:
            raise ValueError("only one air long action may attach to one air")
        self.direction = AirDirection.UP
        self._long_action = AirSlide(self.tick, self.x, self.width, height=height)
        return self._long_action

    def hold(self, *, height: int) -> AirHold:
        if self._long_action is not None:
            raise ValueError("only one air long action may attach to one air")
        self.direction = AirDirection.UP
        self._long_action = AirHold(self.tick, self.x, self.width, height=height)
        return self._long_action

    def __str__(self) -> str:
        parts = [
            f"tick={int(self.tick)}",
            f"x={self.x}",
            f"width={self.width}",
            f"direction={_hl_enum_line(self.direction)}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if self.inverted:
            parts.append("inverted=True")
        head = ", ".join(parts)
        if self._long_action is None:
            return f"Air({head})"
        return f"Air({head})\n  {self._long_action!s}"

    __repr__ = __str__

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        note = LLNote(info=self._info.copy(), _id=self._id)
        if self._long_action is not None:
            note.children.append(
                self._long_action.to_ll(skip_validation=skip_validation)  # type: ignore[union-attr]
            )
        return note


class _GroundNote(_GeometryInfoMixin, _ShiftMixin):
    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        _type: NoteType,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        self._type = _type
        self._info = _copy_info(_info)
        self._id = _id
        self._air: Air | None = None
        self._info.type = _type
        self._info.long_attr = LongAttr.NONE
        self.tick = tick
        self.x = x
        self.width = width
        _check_tick(self.tick)
        _check_width(self.width)

    @property
    def type(self) -> NoteType:
        return self._type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.NONE

    height = _info_property("height")

    def air(self, direction: AirDirection) -> Air:
        if self._air is not None:
            raise ValueError("only one air object may attach to one ground note")
        self._air = Air(self.tick, self.x, self.width, direction)
        self._air._attach_to(self)
        return self._air

    def _base_ll(self) -> LLNote:
        return LLNote(info=self._info.copy(), _id=self._id)

    def __str__(self) -> str:
        parts = [
            f"tick={int(self.tick)}",
            f"x={self.x}",
            f"width={self.width}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        head = ", ".join(parts)
        if self._air is None:
            return f"{self.__class__.__name__}({head})"
        air_lines = str(self._air).splitlines()
        return f"{self.__class__.__name__}({head})\n" + "\n".join(f"  {line}" for line in air_lines)

    __repr__ = __str__

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        note = self._base_ll()
        if self._air is not None:
            note.children.append(self._air.to_ll(skip_validation=skip_validation))
        return note


class Tap(_GroundNote):
    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.TAP, _copy_info(_info), _id)


class Damage(_GroundNote):
    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.DAMAGE, _copy_info(_info), _id)


class Extap(_GroundNote):
    direction = _direction_property(ExtapDirection, "extap")

    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        direction: ExtapDirection | int = ExtapDirection.UP,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.EXTAP, _copy_info(_info), _id)
        self.direction = direction

    def _base_ll(self) -> LLNote:
        note = super()._base_ll()
        note.direction = self.direction
        return note

    def __str__(self) -> str:
        parts = [
            f"tick={int(self.tick)}",
            f"x={self.x}",
            f"width={self.width}",
            f"direction={_hl_enum_line(self.direction)}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        head = ", ".join(parts)
        if self._air is None:
            return f"{self.__class__.__name__}({head})"
        air_lines = str(self._air).splitlines()
        return f"{self.__class__.__name__}({head})\n" + "\n".join(f"  {line}" for line in air_lines)


class Flick(Extap):
    direction = _direction_property(FlickDirection, "flick")

    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        direction: FlickDirection | int = FlickDirection.AUTO,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, direction=direction, _info=_info, _id=_id)
        self._type = NoteType.FLICK
        self._info.type = NoteType.FLICK


class Joint(_GeometryInfoMixin):
    long_attr = _info_property("long_attr", LongAttr)
    height = _info_property("height")

    @property
    def info(self) -> NoteInfo:
        return self._info

    @info.setter
    def info(self, value: NoteInfo) -> None:
        self._info = value

    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        long_attr: LongAttr,
        height: int = 800,
        info: NoteInfo | None = None,
        _id: int | None = None,
        air: Air | None = None,
    ) -> None:
        self.info = _copy_info(info)
        self._id = _id
        self.air = air
        self.tick = tick
        self.x = x
        self.width = width
        self.long_attr = long_attr
        self.height = height


class _LongBuilder(_GeometryInfoMixin, _ShiftMixin):
    _note_type: NoteType

    direction = _info_property("direction")
    height = _info_property("height")

    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        height: int = 800,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        _check_tick(tick)
        _check_width(width)
        self._info = _copy_info(_info)
        self._id = _id
        self._joints: list[Joint] = []
        self._ended = False
        self._info.type = self._note_type
        self._info.long_attr = LongAttr.BEGIN
        self.tick = tick
        self.x = x
        self.width = width
        self.height = height

    @property
    def type(self) -> NoteType:
        return self._note_type

    @property
    def long_attr(self) -> LongAttr:
        return LongAttr.BEGIN

    @property
    def joints(self) -> list[Joint]:
        return self._joints

    @property
    def duration(self) -> int:
        return int(self._joints[-1].tick) - int(self.tick)

    def _add_joint(self, joint: Joint) -> None:
        if self._ended:
            raise ValueError("long note already ended")
        _check_tick(joint.tick)
        _check_width(joint.width)
        previous_tick = int(self._joints[-1].tick if self._joints else self.tick)
        if int(joint.tick) <= previous_tick:
            raise ValueError("joint tick must be later than previous joint")
        self._joints.append(joint)
        if joint.long_attr in (LongAttr.END, LongAttr.END_NOACT):
            self._ended = True

    def _require_end(self) -> Joint:
        if not self._joints or self._joints[-1].long_attr not in (
            LongAttr.END,
            LongAttr.END_NOACT,
        ):
            raise ValueError("long note requires an end joint")
        return self._joints[-1]

    def _joint_geometry(
        self,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> tuple[int, int, int]:
        previous = self._joints[-1] if self._joints else self
        return (
            previous.x if x is None else x,
            previous.width if width is None else width,
            previous.height if height is None else height,
        )

    def _to_ll_tree(
        self, begin_attr: LongAttr = LongAttr.BEGIN, *, skip_validation: bool = False
    ) -> LLNote:
        if not skip_validation:
            self._require_end()
        root = LLNote(
            info=self._info.copy(long_attr=begin_attr),
            _id=self._id,
        )
        for joint in self._joints:
            jinfo = joint.info.copy(type=self._note_type)
            if self._note_type is NoteType.AIRCRUSH:
                jinfo = jinfo.copy(option_value=0)
            child = LLNote(
                info=jinfo,
                _id=joint._id,
            )
            if joint.air is not None:
                child.children.append(joint.air.to_ll(skip_validation=skip_validation))
            root.children.append(child)
        return root

    def __str__(self) -> str:
        cls = self.__class__.__name__
        parts = [
            f"tick={int(self.tick)}",
            f"x={self.x}",
            f"width={self.width}",
            f"height={self.height}",
        ]
        if self._id is not None:
            parts.append(f"id={self._id}")
        if isinstance(self, AirCrush):
            parts.append(f"density={self.density}")
            parts.append(f"color={_hl_enum_line(self.color)}")
        head = ", ".join(parts)
        if not self._joints:
            return f"{cls}({head})"
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
            jinner = ", ".join(jbits)
            if j.air is None:
                joint_strs.append(f"Joint({jinner})")
            else:
                joint_strs.append(f"Joint({jinner}, air={j.air!s})")
        return f"{cls}({head}, joints=[{', '.join(joint_strs)}])"

    __repr__ = __str__


class Slide(_LongBuilder):
    _note_type = NoteType.SLIDE

    def step(self, tick: int, *, x: int | None = None, width: int | None = None) -> Slide:
        x, width, height = self._joint_geometry(x=x, width=width)
        self._add_joint(Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.STEP))
        return self

    def control(self, tick: int, *, x: int | None = None, width: int | None = None) -> Slide:
        x, width, height = self._joint_geometry(x=x, width=width)
        self._add_joint(
            Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.CONTROL)
        )
        return self

    def curve_control(self, tick: int, *, x: int | None = None, width: int | None = None) -> Slide:
        x, width, height = self._joint_geometry(x=x, width=width)
        self._add_joint(
            Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                long_attr=LongAttr.CURVE_CONTROL,
            )
        )
        return self

    def end(self, tick: int, *, x: int | None = None, width: int | None = None) -> Slide:
        x, width, height = self._joint_geometry(x=x, width=width)
        self._add_joint(Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END))
        return self

    def air(self, direction: AirDirection) -> Air:
        end = self._require_end()
        if end.air is not None:
            raise ValueError("only one air object may attach to one ground note")
        end.air = Air(end.tick, end.x, end.width, direction)
        end.air._attach_to(self)
        return end.air

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        return self._to_ll_tree(skip_validation=skip_validation)


class Hold(_LongBuilder):
    _note_type = NoteType.HOLD

    def end(self, tick: int, *, x: int | None = None, width: int | None = None) -> Hold:
        self._add_joint(
            Joint(
                tick=tick,
                x=self.x if x is None else x,
                width=self.width if width is None else width,
                long_attr=LongAttr.END,
            )
        )
        return self

    def air(self, direction: AirDirection) -> Air:
        end = self._require_end()
        if end.air is not None:
            raise ValueError("only one air object may attach to one ground note")
        end.air = Air(end.tick, end.x, end.width, direction)
        end.air._attach_to(self)
        return end.air

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        return self._to_ll_tree(skip_validation=skip_validation)


class AirSlide(_LongBuilder):
    _note_type = NoteType.AIRSLIDE

    def step(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirSlide:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.STEP))
        return self

    def control(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirSlide:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(
            Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.CONTROL)
        )
        return self

    def curve_control(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirSlide:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(
            Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                long_attr=LongAttr.CURVE_CONTROL,
            )
        )
        return self

    def end(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirSlide:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END))
        return self

    def end_noact(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirSlide:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(
            Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END_NOACT)
        )
        return self

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        return self._to_ll_tree(skip_validation=skip_validation)


class AirHold(_LongBuilder):
    _note_type = NoteType.AIRHOLD

    def step(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirHold:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.STEP))
        return self

    def end(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirHold:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END))
        return self

    def end_noact(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirHold:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(
            Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END_NOACT)
        )
        return self

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        return self._to_ll_tree(skip_validation=skip_validation)


class AirCrush(_LongBuilder):
    _note_type = NoteType.AIRCRUSH

    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        height: int,
        density: AirCrushOption | int,
        color: AirCrushColor = AirCrushColor.DEF,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, height=height, _info=_info, _id=_id)
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
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirCrush:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(
            Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                long_attr=LongAttr.CONTROL,
            )
        )
        return self

    def end(
        self,
        tick: int,
        *,
        x: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AirCrush:
        x, width, height = self._joint_geometry(x=x, width=width, height=height)
        self._add_joint(
            Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                long_attr=LongAttr.END,
            )
        )
        return self

    def to_ll(self, *, skip_validation: bool = False) -> LLNote:
        return self._to_ll_tree(skip_validation=skip_validation)


def wrap_ll_note(note: LLNote) -> HLNote:
    if note.type in (NoteType.TAP, NoteType.EXTAP, NoteType.FLICK, NoteType.DAMAGE):
        return _wrap_ground(note)
    if note.type is NoteType.HOLD:
        return _wrap_hold(note)
    if note.type is NoteType.SLIDE:
        return _wrap_slide(note)
    if note.type is NoteType.AIRCRUSH:
        return _wrap_air_crush(note)
    raise UnsupportedNoteTree(f"unsupported root note type: {note.type.name}")


def _wrap_ground(note: LLNote) -> HLNote:
    if note.long_attr is not LongAttr.NONE:
        raise UnsupportedNoteTree("ground note must not have long_attr")
    if note.type is NoteType.TAP:
        wrapped: _GroundNote = Tap(
            int(note.tick), note.x, note.width, _info=note.info, _id=note._id
        )
    elif note.type is NoteType.EXTAP:
        try:
            wrapped = Extap(
                int(note.tick),
                note.x,
                note.width,
                direction=note.direction,
                _info=note.info,
                _id=note._id,
            )
        except ValueError as exc:
            raise UnsupportedNoteTree("unsupported extap direction") from exc
    elif note.type is NoteType.FLICK:
        try:
            wrapped = Flick(
                int(note.tick),
                note.x,
                note.width,
                direction=note.direction,
                _info=note.info,
                _id=note._id,
            )
        except ValueError as exc:
            raise UnsupportedNoteTree("unsupported flick direction") from exc
    elif note.type is NoteType.DAMAGE:
        wrapped = Damage(int(note.tick), note.x, note.width, _info=note.info, _id=note._id)
    else:
        raise UnsupportedNoteTree("unsupported ground note")

    if len(note.children) > 1:
        raise UnsupportedNoteTree("only one air object may attach to one ground note")
    if note.children:
        child = note.children[0]
        if child.type is not NoteType.AIR:
            raise UnsupportedNoteTree("ground note child must be AIR")
        try:
            wrapped_air = wrapped.air(child.direction)
        except ValueError as exc:
            raise UnsupportedNoteTree("unsupported air direction") from exc
        wrapped_air._info = child.info.copy()
        wrapped_air._id = child._id
        if len(child.children) > 1:
            raise UnsupportedNoteTree("air may have only one long action")
        if child.children:
            wrapped_air._long_action = _wrap_air_action(child.children[0])
    return wrapped


def _check_ll_root_begin(note: LLNote, expected: NoteType) -> None:
    if note.type is not expected or note.long_attr is not LongAttr.BEGIN:
        raise UnsupportedNoteTree("long note root must be BEGIN")


def _check_order(previous_tick: int, tick: int) -> None:
    if int(tick) <= int(previous_tick):
        raise UnsupportedNoteTree("long note joints must be strictly chronological")


def _require_final_end(children: list[LLNote], allowed: set[LongAttr]) -> None:
    if not children or children[-1].long_attr not in allowed:
        raise UnsupportedNoteTree("long note must end with an end joint")


def _copy_joint(builder: _LongBuilder, child: LLNote) -> None:
    builder._joints[-1].info = child.info.copy()
    builder._joints[-1]._id = child._id
    if child.children:
        builder._joints[-1].air = _wrap_attached_air(child.children)


def _wrap_attached_air(children: list[LLNote]) -> Air:
    if len(children) != 1:
        raise UnsupportedNoteTree("long note joint may have only one air object")
    child = children[0]
    if child.type is not NoteType.AIR:
        raise UnsupportedNoteTree("long note joint child must be AIR")
    try:
        air = Air(
            int(child.tick),
            child.x,
            child.width,
            child.direction,
            _info=child.info.copy(),
            _id=child._id,
        )
    except ValueError as exc:
        raise UnsupportedNoteTree("unsupported air direction") from exc
    if len(child.children) > 1:
        raise UnsupportedNoteTree("air may have only one long action")
    if child.children:
        air._long_action = _wrap_air_action(child.children[0])
    return air


def _wrap_slide(note: LLNote) -> Slide:
    _check_ll_root_begin(note, NoteType.SLIDE)
    _require_final_end(note.children, {LongAttr.END})
    slide = Slide(
        int(note.tick), note.x, note.width, height=note.height, _info=note.info, _id=note._id
    )
    previous_tick = int(note.tick)
    for child in note.children:
        _check_order(previous_tick, int(child.tick))
        if child.long_attr is LongAttr.STEP:
            slide.step(int(child.tick), x=child.x, width=child.width)
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(int(child.tick), x=child.x, width=child.width)
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide.curve_control(int(child.tick), x=child.x, width=child.width)
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            slide.end(int(child.tick), x=child.x, width=child.width)
        else:
            raise UnsupportedNoteTree("unsupported slide joint")
        _copy_joint(slide, child)
        previous_tick = int(child.tick)
    return slide


def _wrap_hold(note: LLNote) -> Hold:
    _check_ll_root_begin(note, NoteType.HOLD)
    if len(note.children) != 1 or note.children[0].long_attr is not LongAttr.END:
        raise UnsupportedNoteTree("hold must have exactly one end joint")
    child = note.children[0]
    _check_order(int(note.tick), int(child.tick))
    hold = Hold(
        int(note.tick), note.x, note.width, height=note.height, _info=note.info, _id=note._id
    )
    hold.end(int(child.tick), x=child.x, width=child.width)
    _copy_joint(hold, child)
    return hold


def _wrap_air_action(note: LLNote) -> AirSlide | AirHold:
    if note.type is NoteType.AIRSLIDE:
        return _wrap_air_slide(note)
    if note.type is NoteType.AIRHOLD:
        return _wrap_air_hold(note)
    raise UnsupportedNoteTree("air child must be AIRSLIDE or AIRHOLD")


def _wrap_air_slide(note: LLNote) -> AirSlide:
    _check_ll_root_begin(note, NoteType.AIRSLIDE)
    _require_final_end(note.children, {LongAttr.END, LongAttr.END_NOACT})
    slide = AirSlide(
        int(note.tick), note.x, note.width, height=note.height, _info=note.info, _id=note._id
    )
    previous_tick = int(note.tick)
    for child in note.children:
        _check_order(previous_tick, int(child.tick))
        if child.long_attr is LongAttr.STEP:
            slide.step(int(child.tick), x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(int(child.tick), x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide.curve_control(int(child.tick), x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            slide.end(int(child.tick), x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.END_NOACT and child is note.children[-1]:
            slide.end_noact(int(child.tick), x=child.x, width=child.width, height=child.height)
        else:
            raise UnsupportedNoteTree("unsupported air slide joint")
        _copy_joint(slide, child)
        previous_tick = int(child.tick)
    return slide


def _wrap_air_hold(note: LLNote) -> AirHold:
    _check_ll_root_begin(note, NoteType.AIRHOLD)
    _require_final_end(note.children, {LongAttr.END, LongAttr.END_NOACT})
    hold = AirHold(
        int(note.tick), note.x, note.width, height=note.height, _info=note.info, _id=note._id
    )
    previous_tick = int(note.tick)
    for child in note.children:
        _check_order(previous_tick, int(child.tick))
        if child.long_attr is LongAttr.STEP:
            hold.step(int(child.tick), x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            hold.end(int(child.tick), x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.END_NOACT and child is note.children[-1]:
            hold.end_noact(int(child.tick), x=child.x, width=child.width, height=child.height)
        else:
            raise UnsupportedNoteTree("unsupported air hold joint")
        _copy_joint(hold, child)
        previous_tick = int(child.tick)
    return hold


def _wrap_air_crush(note: LLNote) -> AirCrush:
    _check_ll_root_begin(note, NoteType.AIRCRUSH)
    _require_final_end(note.children, {LongAttr.END})
    crush = AirCrush(
        int(note.tick),
        note.x,
        note.width,
        height=note.height,
        density=note.option_value,
        color=cast(AirCrushColor, note.variation_id),
        _info=note.info,
        _id=note._id,
    )
    previous_tick = int(note.tick)
    for child in note.children:
        _check_order(previous_tick, int(child.tick))
        if child.long_attr is LongAttr.CONTROL:
            crush.control(
                int(child.tick),
                x=child.x,
                width=child.width,
                height=child.height,
            )
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            crush.end(
                int(child.tick),
                x=child.x,
                width=child.width,
                height=child.height,
            )
        else:
            raise UnsupportedNoteTree("unsupported air crush joint")
        _copy_joint(crush, child)
        previous_tick = int(child.tick)
    return crush
