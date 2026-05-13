from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from margrete_rpc.model.ll_note import LLNote, NoteInfo
from margrete_rpc.model.note_types import Direction, LongAttr, NoteType


class UnsupportedNoteTree(ValueError):
    pass


@runtime_checkable
class HLNote(Protocol):
    def to_ll(self) -> LLNote:
        raise NotImplementedError


def _check_tick(tick: int) -> None:
    if tick < 0:
        raise ValueError("tick must be non-negative")


def _check_width(width: int) -> None:
    if width < 1:
        raise ValueError("width must be at least 1")


def _copy_info(info: NoteInfo | None) -> NoteInfo:
    return info.copy() if info is not None else NoteInfo()


@dataclass
class Air:
    tick: int
    x: int
    width: int
    direction: Direction
    _info: NoteInfo = field(default_factory=NoteInfo)
    _id: int | None = None
    _parent_id: int | None = None
    _long_action: object | None = None

    def __post_init__(self) -> None:
        _check_tick(self.tick)
        _check_width(self.width)

    def _attach_to(self, parent: object) -> None:
        parent_id = id(parent)
        if self._parent_id is not None and self._parent_id != parent_id:
            raise ValueError("one air object cannot attach to many ground notes")
        self._parent_id = parent_id

    def slide(self, *, height: int) -> AirSlide:
        if self._long_action is not None:
            raise ValueError("only one air long action may attach to one air")
        self.direction = Direction.UP
        self._long_action = AirSlide(self.tick, self.x, self.width, height=height)
        return self._long_action

    def hold(self, *, height: int) -> AirHold:
        if self._long_action is not None:
            raise ValueError("only one air long action may attach to one air")
        self.direction = Direction.UP
        self._long_action = AirHold(self.tick, self.x, self.width, height=height)
        return self._long_action

    def to_ll(self) -> LLNote:
        info = self._info.copy(
            type=NoteType.AIR,
            long_attr=LongAttr.NONE,
            direction=self.direction,
            tick=self.tick,
            x=self.x,
            width=self.width,
        )
        note = LLNote(info=info, id=self._id)
        if self._long_action is not None:
            note.children.append(self._long_action.to_ll())
        return note


@dataclass
class _PositiveNote:
    tick: int
    x: int
    width: int
    _type: NoteType
    _info: NoteInfo = field(default_factory=NoteInfo)
    _id: int | None = None
    _air: Air | None = None

    def __post_init__(self) -> None:
        _check_tick(self.tick)
        _check_width(self.width)

    def air(self, direction: Direction) -> Air:
        if self._air is not None:
            raise ValueError("only one air object may attach to one ground note")
        self._air = Air(self.tick, self.x, self.width, direction)
        self._air._attach_to(self)
        return self._air

    def _base_ll(self) -> LLNote:
        return LLNote(
            info=self._info.copy(
                type=self._type,
                long_attr=LongAttr.NONE,
                tick=self.tick,
                x=self.x,
                width=self.width,
            ),
            id=self._id,
        )

    def to_ll(self) -> LLNote:
        note = self._base_ll()
        if self._air is not None:
            note.children.append(self._air.to_ll())
        return note


class Tap(_PositiveNote):
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


class Damage(_PositiveNote):
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


class Extap(_PositiveNote):
    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        direction: Direction = Direction.NONE,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, NoteType.EXTAP, _copy_info(_info), _id)
        self.direction = direction

    def _base_ll(self) -> LLNote:
        note = super()._base_ll()
        note.direction = self.direction
        return note


class Flick(Extap):
    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        direction: Direction = Direction.NONE,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, direction=direction, _info=_info, _id=_id)
        self._type = NoteType.FLICK


@dataclass
class _Joint:
    tick: int
    x: int
    width: int
    long_attr: LongAttr
    height: int = 800
    option_value: int = 0
    info: NoteInfo = field(default_factory=NoteInfo)
    id: int | None = None
    air: Air | None = None


class _LongBuilder:
    _note_type: NoteType

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
        self.tick = tick
        self.x = x
        self.width = width
        self.height = height
        self._info = _copy_info(_info)
        self._id = _id
        self._joints: list[_Joint] = []
        self._ended = False

    def _add_joint(self, joint: _Joint) -> None:
        if self._ended:
            raise ValueError("long note already ended")
        _check_tick(joint.tick)
        _check_width(joint.width)
        previous_tick = self._joints[-1].tick if self._joints else self.tick
        if joint.tick <= previous_tick:
            raise ValueError("joint tick must be later than previous joint")
        self._joints.append(joint)
        if joint.long_attr in (LongAttr.END, LongAttr.END_NOACT):
            self._ended = True

    def _require_end(self) -> _Joint:
        if not self._joints or self._joints[-1].long_attr not in (
            LongAttr.END,
            LongAttr.END_NOACT,
        ):
            raise ValueError("long note requires an end joint")
        return self._joints[-1]

    def _to_ll_tree(self, begin_attr: LongAttr = LongAttr.BEGIN) -> LLNote:
        self._require_end()
        root = LLNote(
            info=self._info.copy(
                type=self._note_type,
                long_attr=begin_attr,
                tick=self.tick,
                x=self.x,
                width=self.width,
                height=self.height,
            ),
            id=self._id,
        )
        for joint in self._joints:
            child = LLNote(
                info=joint.info.copy(
                    type=self._note_type,
                    long_attr=joint.long_attr,
                    tick=joint.tick,
                    x=joint.x,
                    width=joint.width,
                    height=joint.height,
                    option_value=joint.option_value,
                ),
                id=joint.id,
            )
            if joint.air is not None:
                child.children.append(joint.air.to_ll())
            root.children.append(child)
        return root


class Slide(_LongBuilder):
    _note_type = NoteType.SLIDE

    def step(self, tick: int, *, x: int, width: int) -> Slide:
        self._add_joint(_Joint(tick=tick, x=x, width=width, long_attr=LongAttr.STEP))
        return self

    def control(self, tick: int, *, x: int, width: int) -> Slide:
        self._add_joint(_Joint(tick=tick, x=x, width=width, long_attr=LongAttr.CONTROL))
        return self

    def curve_control(self, tick: int, *, x: int, width: int) -> Slide:
        self._add_joint(_Joint(tick=tick, x=x, width=width, long_attr=LongAttr.CURVE_CONTROL))
        return self

    def end(self, tick: int, *, x: int, width: int) -> Slide:
        self._add_joint(_Joint(tick=tick, x=x, width=width, long_attr=LongAttr.END))
        return self

    def air(self, direction: Direction) -> Air:
        end = self._require_end()
        if end.air is not None:
            raise ValueError("only one air object may attach to one ground note")
        end.air = Air(end.tick, end.x, end.width, direction)
        end.air._attach_to(self)
        return end.air

    def to_ll(self) -> LLNote:
        return self._to_ll_tree()


class Hold(_LongBuilder):
    _note_type = NoteType.HOLD

    def end(self, tick: int, *, x: int | None = None, width: int | None = None) -> Hold:
        self._add_joint(
            _Joint(
                tick=tick,
                x=self.x if x is None else x,
                width=self.width if width is None else width,
                long_attr=LongAttr.END,
            )
        )
        return self

    def air(self, direction: Direction) -> Air:
        end = self._require_end()
        if end.air is not None:
            raise ValueError("only one air object may attach to one ground note")
        end.air = Air(end.tick, end.x, end.width, direction)
        end.air._attach_to(self)
        return end.air

    def to_ll(self) -> LLNote:
        return self._to_ll_tree()


class AirSlide(_LongBuilder):
    _note_type = NoteType.AIRSLIDE

    def step(self, tick: int, *, x: int, width: int, height: int) -> AirSlide:
        self._add_joint(_Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.STEP))
        return self

    def control(self, tick: int, *, x: int, width: int, height: int) -> AirSlide:
        self._add_joint(
            _Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.CONTROL)
        )
        return self

    def curve_control(self, tick: int, *, x: int, width: int, height: int) -> AirSlide:
        self._add_joint(
            _Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                long_attr=LongAttr.CURVE_CONTROL,
            )
        )
        return self

    def end(self, tick: int, *, x: int, width: int, height: int) -> AirSlide:
        self._add_joint(_Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END))
        return self

    def end_noact(self, tick: int, *, x: int, width: int, height: int) -> AirSlide:
        self._add_joint(
            _Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END_NOACT)
        )
        return self

    def to_ll(self) -> LLNote:
        return self._to_ll_tree()


class AirHold(_LongBuilder):
    _note_type = NoteType.AIRHOLD

    def end(self, tick: int, *, x: int, width: int, height: int) -> AirHold:
        self._add_joint(_Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END))
        return self

    def end_noact(self, tick: int, *, x: int, width: int, height: int) -> AirHold:
        self._add_joint(
            _Joint(tick=tick, x=x, width=width, height=height, long_attr=LongAttr.END_NOACT)
        )
        return self

    def to_ll(self) -> LLNote:
        return self._to_ll_tree()


class AirCrush(_LongBuilder):
    _note_type = NoteType.AIRCRUSH

    def __init__(
        self,
        tick: int,
        x: int,
        width: int,
        *,
        height: int,
        option_value: int,
        variation_id: int = 0,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        super().__init__(tick, x, width, height=height, _info=_info, _id=_id)
        self.option_value = int(option_value)
        self.variation_id = int(variation_id)

    def control(self, tick: int, *, x: int, width: int, height: int, option_value: int) -> AirCrush:
        self._add_joint(
            _Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                option_value=int(option_value),
                long_attr=LongAttr.CONTROL,
            )
        )
        return self

    def end(self, tick: int, *, x: int, width: int, height: int, option_value: int) -> AirCrush:
        self._add_joint(
            _Joint(
                tick=tick,
                x=x,
                width=width,
                height=height,
                option_value=int(option_value),
                long_attr=LongAttr.END,
            )
        )
        return self

    def to_ll(self) -> LLNote:
        note = self._to_ll_tree()
        note.option_value = self.option_value
        note.variation_id = self.variation_id
        return note


def wrap_ll_note(note: LLNote) -> HLNote:
    if note.type in (NoteType.TAP, NoteType.EXTAP, NoteType.FLICK, NoteType.DAMAGE):
        return _wrap_positive(note)
    if note.type is NoteType.HOLD:
        return _wrap_hold(note)
    if note.type is NoteType.SLIDE:
        return _wrap_slide(note)
    if note.type is NoteType.AIRCRUSH:
        return _wrap_air_crush(note)
    raise UnsupportedNoteTree(f"unsupported root note type: {note.type.name}")


def _wrap_positive(note: LLNote) -> HLNote:
    if note.long_attr is not LongAttr.NONE:
        raise UnsupportedNoteTree("positive note must not have long_attr")
    if note.type is NoteType.TAP:
        wrapped: _PositiveNote = Tap(note.tick, note.x, note.width, _info=note.info, _id=note.id)
    elif note.type is NoteType.EXTAP:
        wrapped = Extap(
            note.tick,
            note.x,
            note.width,
            direction=note.direction,
            _info=note.info,
            _id=note.id,
        )
    elif note.type is NoteType.FLICK:
        wrapped = Flick(
            note.tick,
            note.x,
            note.width,
            direction=note.direction,
            _info=note.info,
            _id=note.id,
        )
    elif note.type is NoteType.DAMAGE:
        wrapped = Damage(note.tick, note.x, note.width, _info=note.info, _id=note.id)
    else:
        raise UnsupportedNoteTree("unsupported positive note")

    if len(note.children) > 1:
        raise UnsupportedNoteTree("only one air object may attach to one ground note")
    if note.children:
        child = note.children[0]
        if child.type is not NoteType.AIR:
            raise UnsupportedNoteTree("positive note child must be AIR")
        wrapped_air = wrapped.air(child.direction)
        wrapped_air._info = child.info.copy()
        wrapped_air._id = child.id
        if len(child.children) > 1:
            raise UnsupportedNoteTree("air may have only one long action")
        if child.children:
            wrapped_air._long_action = _wrap_air_action(child.children[0])
    return wrapped


def _check_ll_root_begin(note: LLNote, expected: NoteType) -> None:
    if note.type is not expected or note.long_attr is not LongAttr.BEGIN:
        raise UnsupportedNoteTree("long note root must be BEGIN")


def _check_order(previous_tick: int, tick: int) -> None:
    if tick <= previous_tick:
        raise UnsupportedNoteTree("long note joints must be strictly chronological")


def _require_final_end(children: list[LLNote], allowed: set[LongAttr]) -> None:
    if not children or children[-1].long_attr not in allowed:
        raise UnsupportedNoteTree("long note must end with an end joint")


def _copy_joint(builder: _LongBuilder, child: LLNote) -> None:
    builder._joints[-1].info = child.info.copy()
    builder._joints[-1].id = child.id
    if child.children:
        builder._joints[-1].air = _wrap_attached_air(child.children)


def _wrap_attached_air(children: list[LLNote]) -> Air:
    if len(children) != 1:
        raise UnsupportedNoteTree("long note joint may have only one air object")
    child = children[0]
    if child.type is not NoteType.AIR:
        raise UnsupportedNoteTree("long note joint child must be AIR")
    air = Air(
        child.tick, child.x, child.width, child.direction, _info=child.info.copy(), _id=child.id
    )
    if len(child.children) > 1:
        raise UnsupportedNoteTree("air may have only one long action")
    if child.children:
        air._long_action = _wrap_air_action(child.children[0])
    return air


def _wrap_slide(note: LLNote) -> Slide:
    _check_ll_root_begin(note, NoteType.SLIDE)
    _require_final_end(note.children, {LongAttr.END})
    slide = Slide(note.tick, note.x, note.width, height=note.height, _info=note.info, _id=note.id)
    previous_tick = note.tick
    for child in note.children:
        _check_order(previous_tick, child.tick)
        if child.long_attr is LongAttr.STEP:
            slide.step(child.tick, x=child.x, width=child.width)
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(child.tick, x=child.x, width=child.width)
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide.curve_control(child.tick, x=child.x, width=child.width)
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            slide.end(child.tick, x=child.x, width=child.width)
        else:
            raise UnsupportedNoteTree("unsupported slide joint")
        _copy_joint(slide, child)
        previous_tick = child.tick
    return slide


def _wrap_hold(note: LLNote) -> Hold:
    _check_ll_root_begin(note, NoteType.HOLD)
    if len(note.children) != 1 or note.children[0].long_attr is not LongAttr.END:
        raise UnsupportedNoteTree("hold must have exactly one end joint")
    child = note.children[0]
    _check_order(note.tick, child.tick)
    hold = Hold(note.tick, note.x, note.width, height=note.height, _info=note.info, _id=note.id)
    hold.end(child.tick, x=child.x, width=child.width)
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
        note.tick, note.x, note.width, height=note.height, _info=note.info, _id=note.id
    )
    previous_tick = note.tick
    for child in note.children:
        _check_order(previous_tick, child.tick)
        if child.long_attr is LongAttr.STEP:
            slide.step(child.tick, x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(child.tick, x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide.curve_control(child.tick, x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            slide.end(child.tick, x=child.x, width=child.width, height=child.height)
        elif child.long_attr is LongAttr.END_NOACT and child is note.children[-1]:
            slide.end_noact(child.tick, x=child.x, width=child.width, height=child.height)
        else:
            raise UnsupportedNoteTree("unsupported air slide joint")
        _copy_joint(slide, child)
        previous_tick = child.tick
    return slide


def _wrap_air_hold(note: LLNote) -> AirHold:
    _check_ll_root_begin(note, NoteType.AIRHOLD)
    if len(note.children) != 1 or note.children[0].long_attr not in (
        LongAttr.END,
        LongAttr.END_NOACT,
    ):
        raise UnsupportedNoteTree("air hold must have exactly one end joint")
    child = note.children[0]
    _check_order(note.tick, child.tick)
    hold = AirHold(note.tick, note.x, note.width, height=note.height, _info=note.info, _id=note.id)
    if child.long_attr is LongAttr.END:
        hold.end(child.tick, x=child.x, width=child.width, height=child.height)
    else:
        hold.end_noact(child.tick, x=child.x, width=child.width, height=child.height)
    _copy_joint(hold, child)
    return hold


def _wrap_air_crush(note: LLNote) -> AirCrush:
    _check_ll_root_begin(note, NoteType.AIRCRUSH)
    _require_final_end(note.children, {LongAttr.END})
    crush = AirCrush(
        note.tick,
        note.x,
        note.width,
        height=note.height,
        option_value=note.option_value,
        variation_id=note.variation_id,
        _info=note.info,
        _id=note.id,
    )
    previous_tick = note.tick
    for child in note.children:
        _check_order(previous_tick, child.tick)
        if child.long_attr is LongAttr.CONTROL:
            crush.control(
                child.tick,
                x=child.x,
                width=child.width,
                height=child.height,
                option_value=child.option_value,
            )
        elif child.long_attr is LongAttr.END and child is note.children[-1]:
            crush.end(
                child.tick,
                x=child.x,
                width=child.width,
                height=child.height,
                option_value=child.option_value,
            )
        else:
            raise UnsupportedNoteTree("unsupported air crush joint")
        _copy_joint(crush, child)
        previous_tick = child.tick
    return crush
