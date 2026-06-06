from __future__ import annotations

from ..raw import RawNote
from .air import Air, AirHold, AirSlide
from .color import color_from_value
from .ground import Damage, Extap, Flick, Tap, _GroundNote
from .joint import _JointHostBase
from .long import AirCrush, Hold, Slide
from .shared import Note, UnsupportedNoteTree
from .types import LongAttr, NoteInfo, NoteType


def wrap_raw_note(note: RawNote) -> Note:
    if note.type in (NoteType.TAP, NoteType.EXTAP, NoteType.FLICK, NoteType.DAMAGE):
        return _wrap_ground(note)
    if note.type is NoteType.HOLD:
        return _wrap_hold(note)
    if note.type is NoteType.SLIDE:
        return _wrap_slide(note)
    if note.type is NoteType.AIRCRUSH:
        return _wrap_air_crush(note)
    raise UnsupportedNoteTree(f"unsupported root note type: {note.type.name}")


def _restore_wrapped_info(wrapped: _GroundNote, note: RawNote) -> None:
    wrapped._info = note.info.copy()
    wrapped._id = note._id


def _wrap_ground(note: RawNote) -> Note:
    if note.long_attr is not LongAttr.NONE:
        raise UnsupportedNoteTree("ground note must not have long_attr")
    if note.type is NoteType.TAP:
        wrapped: _GroundNote = Tap(int(note.t), note.x, note.w, _info=note.info, _id=note._id)
    elif note.type is NoteType.EXTAP:
        wrapped = Extap(int(note.t), note.x, note.w)
        _restore_wrapped_info(wrapped, note)
    elif note.type is NoteType.FLICK:
        wrapped = Flick(int(note.t), note.x, note.w)
        _restore_wrapped_info(wrapped, note)
    elif note.type is NoteType.DAMAGE:
        wrapped = Damage(int(note.t), note.x, note.w, _info=note.info, _id=note._id)
    else:
        raise UnsupportedNoteTree("unsupported ground note")

    if len(note.children) > 1:
        raise UnsupportedNoteTree("only one air object may attach to one ground note")
    if note.children:
        wrapped.tie(_wrap_attached_air_note(note.children[0]))
    return wrapped


def _check_node_root_begin(note: RawNote, expected: NoteType) -> None:
    if note.type is not expected or note.long_attr is not LongAttr.BEGIN:
        raise UnsupportedNoteTree("long note root must be BEGIN")


def _check_order(previous_t: int, t: int) -> None:
    if int(t) <= int(previous_t):
        raise UnsupportedNoteTree("long note joints must be strictly chronological")


def _require_final_end(children: list[RawNote], allowed: set[LongAttr]) -> None:
    if not children or children[-1].long_attr not in allowed:
        raise UnsupportedNoteTree("long note must end with an end joint")


def _copy_joint(builder: _JointHostBase, child: RawNote) -> None:
    joint = builder._joints[-1]
    joint._info = child.info.copy(type=NoteType.UNKNOWN, long_attr=LongAttr.NONE)
    joint._id = child._id


def _wrap_attached_air_note(note: RawNote) -> Air | AirSlide | AirHold:
    if note.type is not NoteType.AIR:
        raise UnsupportedNoteTree("attached note child must be AIR")
    if len(note.children) > 1:
        raise UnsupportedNoteTree("air may have only one long action")
    if not note.children:
        try:
            return Air(note.dir, _info=note.info.copy(), _id=note._id)
        except ValueError as exc:
            raise UnsupportedNoteTree("unsupported air direction") from exc
    action = note.children[0]
    if action.type is NoteType.AIRSLIDE:
        return _wrap_air_slide(action, air_info=note.info.copy(), air_id=note._id)
    if action.type is NoteType.AIRHOLD:
        return _wrap_air_hold(action, air_info=note.info.copy(), air_id=note._id)
    raise UnsupportedNoteTree("air child must be AIRSLIDE or AIRHOLD")


def _ensure_air_only_on_end(child: RawNote, is_final: bool) -> None:
    if child.children and not is_final:
        raise UnsupportedNoteTree("air may attach only to the end joint")


def _wrap_slide(note: RawNote) -> Slide:
    _check_node_root_begin(note, NoteType.SLIDE)
    _require_final_end(note.children, {LongAttr.END})
    slide = Slide(int(note.t), note.x, note.w, _info=note.info, _id=note._id)
    previous_t = int(note.t)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_t, int(child.t))
        _ensure_air_only_on_end(child, is_final)
        if child.long_attr is LongAttr.STEP:
            slide.step(int(child.t), x=child.x, w=child.w)
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(int(child.t), x=child.x, w=child.w)
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide._add_curve_control(int(child.t), child.x, child.w)
        elif child.long_attr is LongAttr.END and is_final:
            slide.step(int(child.t), x=child.x, w=child.w)
        else:
            raise UnsupportedNoteTree("unsupported slide joint")
        _copy_joint(slide, child)
        if child.children:
            slide.tie(_wrap_attached_air_note(child.children[0]))
        previous_t = int(child.t)
    return slide


def _wrap_hold(note: RawNote) -> Hold:
    _check_node_root_begin(note, NoteType.HOLD)
    if len(note.children) != 1 or note.children[0].long_attr is not LongAttr.END:
        raise UnsupportedNoteTree("hold must have exactly one end joint")
    child = note.children[0]
    _check_order(int(note.t), int(child.t))
    hold = Hold(int(note.t), note.x, note.w, _info=note.info, _id=note._id)
    hold._add_step(int(child.t), x=child.x, w=child.w)
    _copy_joint(hold, child)
    if child.children:
        hold.tie(_wrap_attached_air_note(child.children[0]))
    return hold


def _wrap_air_slide(
    note: RawNote,
    *,
    air_info: NoteInfo | None = None,
    air_id: int | None = None,
) -> AirSlide:
    _check_node_root_begin(note, NoteType.AIRSLIDE)
    _require_final_end(note.children, {LongAttr.END, LongAttr.END_NOACT})
    slide = AirSlide(
        h=note.h,
        _air_info=air_info,
        _air_id=air_id,
        _info=note.info,
        _id=note._id,
    )
    previous_t = int(note.t)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_t, int(child.t))
        if child.children:
            raise UnsupportedNoteTree("air slide joints must not have children")
        if child.long_attr is LongAttr.STEP:
            slide.step(int(child.t), x=child.x, w=child.w, h=child.h)
        elif child.long_attr is LongAttr.CONTROL:
            slide.control(int(child.t), x=child.x, w=child.w, h=child.h)
        elif child.long_attr is LongAttr.CURVE_CONTROL:
            slide._add_curve_control(int(child.t), child.x, child.w, child.h)
        elif child.long_attr is LongAttr.END and is_final:
            slide.step(int(child.t), x=child.x, w=child.w, h=child.h)
        elif child.long_attr is LongAttr.END_NOACT and is_final:
            slide.control(int(child.t), x=child.x, w=child.w, h=child.h)
        else:
            raise UnsupportedNoteTree("unsupported air slide joint")
        _copy_joint(slide, child)
        previous_t = int(child.t)
    return slide


def _wrap_air_hold(
    note: RawNote,
    *,
    air_info: NoteInfo | None = None,
    air_id: int | None = None,
) -> AirHold:
    _check_node_root_begin(note, NoteType.AIRHOLD)
    _require_final_end(note.children, {LongAttr.END, LongAttr.END_NOACT})
    hold = AirHold(
        h=note.h,
        _air_info=air_info,
        _air_id=air_id,
        _info=note.info,
        _id=note._id,
    )
    previous_t = int(note.t)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_t, int(child.t))
        if child.children:
            raise UnsupportedNoteTree("air hold joints must not have children")
        if child.long_attr is LongAttr.STEP:
            hold.step(int(child.t), x=child.x, w=child.w, h=child.h)
        elif child.long_attr is LongAttr.CONTROL:
            hold.control(int(child.t), x=child.x, w=child.w, h=child.h)
        elif child.long_attr is LongAttr.END and is_final:
            hold.step(int(child.t), x=child.x, w=child.w, h=child.h)
        elif child.long_attr is LongAttr.END_NOACT and is_final:
            hold.control(int(child.t), x=child.x, w=child.w, h=child.h)
        else:
            raise UnsupportedNoteTree("unsupported air hold joint")
        _copy_joint(hold, child)
        previous_t = int(child.t)
    return hold


def _wrap_air_crush(note: RawNote) -> AirCrush:
    _check_node_root_begin(note, NoteType.AIRCRUSH)
    _require_final_end(note.children, {LongAttr.END})
    crush = AirCrush(
        int(note.t),
        note.x,
        note.w,
        h=note.h,
        gap=note.option_value,
        color=color_from_value(int(note.variation_id)),
        _info=note.info,
        _id=note._id,
    )
    previous_t = int(note.t)
    for index, child in enumerate(note.children):
        is_final = index == len(note.children) - 1
        _check_order(previous_t, int(child.t))
        if child.children:
            raise UnsupportedNoteTree("air crush joints must not have children")
        if child.long_attr is LongAttr.CONTROL:
            crush.control(
                int(child.t),
                x=child.x,
                w=child.w,
                h=child.h,
            )
        elif child.long_attr is LongAttr.END and is_final:
            crush.control(
                int(child.t),
                x=child.x,
                w=child.w,
                h=child.h,
            )
        else:
            raise UnsupportedNoteTree("unsupported air crush joint")
        _copy_joint(crush, child)
        previous_t = int(child.t)
    return crush
