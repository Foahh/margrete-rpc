from __future__ import annotations

from typing import cast

from ..mg import MgNote
from ..types import AirCrushColor, LongAttr, NoteInfo, NoteType
from ._air import Air, AirHold, AirSlide
from ._ground import Damage, Extap, Flick, Tap, _GroundNote
from ._joint import _JointHost
from ._long import AirCrush, Hold, Slide
from ._shared import Note, UnsupportedNoteTree


def wrap_mg_note(note: MgNote) -> Note:
    if note.type in (NoteType.TAP, NoteType.EXTAP, NoteType.FLICK, NoteType.DAMAGE):
        return _wrap_ground(note)
    if note.type is NoteType.HOLD:
        return _wrap_hold(note)
    if note.type is NoteType.SLIDE:
        return _wrap_slide(note)
    if note.type is NoteType.AIRCRUSH:
        return _wrap_air_crush(note)
    raise UnsupportedNoteTree(f"unsupported root note type: {note.type.name}")


def _restore_wrapped_info(wrapped: _GroundNote, note: MgNote) -> None:
    wrapped._info = note.info.copy()
    wrapped._id = note._id


def _wrap_ground(note: MgNote) -> Note:
    if note.long_attr is not LongAttr.NONE:
        raise UnsupportedNoteTree("ground note must not have long_attr")
    if note.type is NoteType.TAP:
        wrapped: _GroundNote = Tap(
            int(note.tick), note.x, note.width, _info=note.info, _id=note._id
        )
    elif note.type is NoteType.EXTAP:
        wrapped = Extap(int(note.tick), note.x, note.width)
        _restore_wrapped_info(wrapped, note)
    elif note.type is NoteType.FLICK:
        wrapped = Flick(int(note.tick), note.x, note.width)
        _restore_wrapped_info(wrapped, note)
    elif note.type is NoteType.DAMAGE:
        wrapped = Damage(int(note.tick), note.x, note.width, _info=note.info, _id=note._id)
    else:
        raise UnsupportedNoteTree("unsupported ground note")

    if len(note.children) > 1:
        raise UnsupportedNoteTree("only one air object may attach to one ground note")
    if note.children:
        wrapped.air(_wrap_attached_air_note(note.children[0]))
    return wrapped


def _check_mg_root_begin(note: MgNote, expected: NoteType) -> None:
    if note.type is not expected or note.long_attr is not LongAttr.BEGIN:
        raise UnsupportedNoteTree("long note root must be BEGIN")


def _check_order(previous_tick: int, tick: int) -> None:
    if int(tick) <= int(previous_tick):
        raise UnsupportedNoteTree("long note joints must be strictly chronological")


def _require_final_end(children: list[MgNote], allowed: set[LongAttr]) -> None:
    if not children or children[-1].long_attr not in allowed:
        raise UnsupportedNoteTree("long note must end with an end joint")


def _copy_joint(builder: _JointHost, child: MgNote, placed_kind: LongAttr) -> None:
    joint = builder._joints[-1]
    joint.info = child.info.copy(long_attr=placed_kind)
    joint._id = child._id
    joint._default_x = False
    joint._default_width = False
    joint._default_height = False


def _wrap_attached_air_note(note: MgNote) -> Air | AirSlide | AirHold:
    if note.type is not NoteType.AIR:
        raise UnsupportedNoteTree("attached note child must be AIR")
    if len(note.children) > 1:
        raise UnsupportedNoteTree("air may have only one long action")
    if not note.children:
        try:
            return Air(note.direction, _info=note.info.copy(), _id=note._id)
        except ValueError as exc:
            raise UnsupportedNoteTree("unsupported air direction") from exc
    action = note.children[0]
    if action.type is NoteType.AIRSLIDE:
        return _wrap_air_slide(action, air_info=note.info.copy(), air_id=note._id)
    if action.type is NoteType.AIRHOLD:
        return _wrap_air_hold(action, air_info=note.info.copy(), air_id=note._id)
    raise UnsupportedNoteTree("air child must be AIRSLIDE or AIRHOLD")


def _ensure_air_only_on_end(child: MgNote, is_final: bool) -> None:
    if child.children and not is_final:
        raise UnsupportedNoteTree("air may attach only to the end joint")


def _wrap_slide(note: MgNote) -> Slide:
    _check_mg_root_begin(note, NoteType.SLIDE)
    _require_final_end(note.children, {LongAttr.END})
    slide = Slide(int(note.tick), note.x, note.width, _info=note.info, _id=note._id)
    previous_tick = int(note.tick)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_tick, int(child.tick))
        _ensure_air_only_on_end(child, is_final)
        if child.long_attr is LongAttr.STEP:
            slide.step(int(child.tick), x=child.x, width=child.width)
            placed_kind = LongAttr.STEP
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(int(child.tick), x=child.x, width=child.width)
            placed_kind = LongAttr.CONTROL
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide.curve_control(int(child.tick), x=child.x, width=child.width)
            placed_kind = LongAttr.CURVE_CONTROL
        elif child.long_attr is LongAttr.END and is_final:
            slide.step(int(child.tick), x=child.x, width=child.width)
            placed_kind = LongAttr.STEP
        else:
            raise UnsupportedNoteTree("unsupported slide joint")
        _copy_joint(slide, child, placed_kind)
        if child.children:
            slide.air(_wrap_attached_air_note(child.children[0]))
        previous_tick = int(child.tick)
    return slide


def _wrap_hold(note: MgNote) -> Hold:
    _check_mg_root_begin(note, NoteType.HOLD)
    if len(note.children) != 1 or note.children[0].long_attr is not LongAttr.END:
        raise UnsupportedNoteTree("hold must have exactly one end joint")
    child = note.children[0]
    _check_order(int(note.tick), int(child.tick))
    hold = Hold(int(note.tick), note.x, note.width, _info=note.info, _id=note._id)
    hold._add_step(int(child.tick), x=child.x, width=child.width, height=child.height)
    _copy_joint(hold, child, LongAttr.STEP)
    if child.children:
        hold.air(_wrap_attached_air_note(child.children[0]))
    return hold


def _wrap_air_slide(
    note: MgNote,
    *,
    air_info: NoteInfo | None = None,
    air_id: int | None = None,
) -> AirSlide:
    _check_mg_root_begin(note, NoteType.AIRSLIDE)
    _require_final_end(note.children, {LongAttr.END, LongAttr.END_NOACT})
    slide = AirSlide(
        height=note.height,
        _air_info=air_info,
        _air_id=air_id,
        _info=note.info,
        _id=note._id,
    )
    previous_tick = int(note.tick)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_tick, int(child.tick))
        if child.children:
            raise UnsupportedNoteTree("air slide joints must not have children")
        if child.long_attr is LongAttr.STEP:
            slide.step(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.STEP
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.CONTROL
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide.curve_control(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.CURVE_CONTROL
        elif child.long_attr is LongAttr.END and is_final:
            slide.step(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.STEP
        elif child.long_attr is LongAttr.END_NOACT and is_final:
            slide.control(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.CONTROL
        else:
            raise UnsupportedNoteTree("unsupported air slide joint")
        _copy_joint(slide, child, placed_kind)
        previous_tick = int(child.tick)
    return slide


def _wrap_air_hold(
    note: MgNote,
    *,
    air_info: NoteInfo | None = None,
    air_id: int | None = None,
) -> AirHold:
    _check_mg_root_begin(note, NoteType.AIRHOLD)
    _require_final_end(note.children, {LongAttr.END, LongAttr.END_NOACT})
    hold = AirHold(
        height=note.height,
        _air_info=air_info,
        _air_id=air_id,
        _info=note.info,
        _id=note._id,
    )
    previous_tick = int(note.tick)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_tick, int(child.tick))
        if child.children:
            raise UnsupportedNoteTree("air hold joints must not have children")
        if child.long_attr is LongAttr.STEP:
            hold.step(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.STEP
        elif child.long_attr is LongAttr.CONTROL:
            hold.control(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.CONTROL
        elif child.long_attr is LongAttr.END and is_final:
            hold.step(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.STEP
        elif child.long_attr is LongAttr.END_NOACT and is_final:
            hold.control(int(child.tick), x=child.x, width=child.width, height=child.height)
            placed_kind = LongAttr.CONTROL
        else:
            raise UnsupportedNoteTree("unsupported air hold joint")
        _copy_joint(hold, child, placed_kind)
        previous_tick = int(child.tick)
    return hold


def _wrap_air_crush(note: MgNote) -> AirCrush:
    _check_mg_root_begin(note, NoteType.AIRCRUSH)
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
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_tick, int(child.tick))
        if child.children:
            raise UnsupportedNoteTree("air crush joints must not have children")
        if child.long_attr is LongAttr.CONTROL:
            crush.control(
                int(child.tick),
                x=child.x,
                width=child.width,
                height=child.height,
            )
            placed_kind = LongAttr.CONTROL
        elif child.long_attr is LongAttr.END and is_final:
            crush.control(
                int(child.tick),
                x=child.x,
                width=child.width,
                height=child.height,
            )
            placed_kind = LongAttr.CONTROL
        else:
            raise UnsupportedNoteTree("unsupported air crush joint")
        _copy_joint(crush, child, placed_kind)
        previous_tick = int(child.tick)
    return crush
