from __future__ import annotations

from typing import Any, Self, cast

from ..constants import DEFAULT_AIRCRUSH_GAP, DEFAULT_H
from ..time import Division, DivisionLike, PositionLike, resolve_division, resolve_tick, tick_to_div
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


class _PlaceableLong(_GeometryInfoMixin, _TransformMixin):
    __slots__ = ("_info", "_id", "_joints", "_air")

    _note_type: NoteType

    def __init__(
        self,
        *,
        t: int | PositionLike,
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
        self.t = resolve_tick(t)
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
    """A ground slide: a long note threading through a sequence of joints.

    Construct with the begin geometry (``t``/``p``, ``x``, ``w``), then add joints with
    :meth:`add_step` / :meth:`add_ctrl` (in place) or :meth:`with_step` / :meth:`with_ctrl`
    (returns a copy). A slide needs at least one joint and must end on a step or control
    joint. An :class:`Air` note may be attached via :attr:`air`.
    """

    __slots__ = ()

    _note_type = NoteType.SLIDE

    def with_step(self, *, t: int | PositionLike, x: int, w: int) -> Self:
        """Return a copy with a step joint appended at the given timing and geometry."""
        copy = self.clone()
        copy.add_step(t=t, x=x, w=w)
        return copy

    def with_ctrl(self, *, t: int | PositionLike, x: int, w: int) -> Self:
        """Return a copy with a control joint appended at the given timing and geometry."""
        copy = self.clone()
        copy.add_ctrl(t=t, x=x, w=w)
        return copy

    def converted[T: (AirSlide, AirCrush)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` carrying this note's geometry and joints."""
        return cast(T, self._converted_to(target, **overrides))

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        """Convert to a :class:`RawNote` tree (begin note with joint children)."""
        return self._to_raw_tree(skip_validation=skip_validation)


class Hold(_AirAttachable, _PlaceableLong, _JointHost):
    """A ground hold: a long note held from its begin to a single end joint.

    Construct with the begin geometry, then set the end with :meth:`with_step` (or
    :meth:`add_step`). An :class:`Air` note may be attached via :attr:`air`.
    """

    __slots__ = ()

    _note_type = NoteType.HOLD

    def with_step(self, *, t: int | PositionLike, x: int, w: int) -> Self:
        """Return a copy whose end joint is set (or moved) to the given timing/geometry.

        Raises:
            ValueError: If the end timing is not later than the hold's begin.
        """
        tick = resolve_tick(t)
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
        """Return a new note of type ``target`` carrying this note's geometry and joints."""
        return cast(T, self._converted_to(target, **overrides))

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        """Convert to a :class:`RawNote` tree (begin note with joint children)."""
        return self._to_raw_tree(skip_validation=skip_validation)


class AirCrush(_HeightMixin, _PlaceableLong, _AirJointHost):
    """An air-crush note: an air-lane long note with height and a color.

    Like a slide but in the air lane: it carries height ``h``, a :attr:`color`, and
    a gap (:attr:`gap`, with the :attr:`interval` beat-fraction view) controlling the
    spacing of generated segments between joints. Add control joints with
    :meth:`with_ctrl` / :meth:`add_ctrl`.

    Special ``gap`` values:

    * :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_TRACELIKE` (``0``): AirTrace (line only).
    * :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_HEADONLY` (``0x7FFFFFFF``): head step only.
    """

    __slots__ = ()

    _note_type = NoteType.AIRCRUSH
    _joint_type = AirJoint

    def __init__(
        self,
        *,
        t: int | PositionLike,
        x: int,
        w: int,
        h: int,
        gap: int | DivisionLike = DEFAULT_AIRCRUSH_GAP,
        color: ColorLike | int = ColorValue.DEFAULT,
        _info: NoteInfo | None = None,
        _id: int | None = None,
    ) -> None:
        """Create an air-crush begin note.

        Args:
            t: Absolute tick or :data:`Position` tuple.
            x: Left lane index.
            w: Width in lane units.
            h: Air height.
            gap: Segment gap as a tick count or ``(numerator, denominator)`` beat fraction.
                Also accepts :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_TRACELIKE`
                and :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_HEADONLY`.
            color: Crush color (:class:`ColorValue` or raw int).
        """
        super().__init__(t=t, x=x, w=w, _info=_info, _id=_id)
        self.h = h
        self.gap = gap
        self.color = color

    @property
    def gap(self) -> int:
        """Segment gap as an int tick count.

        Set with an int tick count or an :data:`DivisionLike` ``(numerator, denominator)``
        beat fraction. Read the fraction form via the :attr:`interval` view.

        Special values:

        * :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_TRACELIKE` (``0``): AirTrace.
        * :data:`~margrete_rpc.chart.notes.AIRCRUSH_GAP_HEADONLY` (``0x7FFFFFFF``): head step only.
        """
        return int(self._info.option_value)

    @gap.setter
    def gap(self, value: int | DivisionLike) -> None:
        self._info.option_value = resolve_division(value)

    @property
    def interval(self) -> Division:
        """Read-only ``(numerator, denominator)`` beat-fraction view of ``gap``."""
        return tick_to_div(int(self._info.option_value))

    @property
    def color(self) -> ColorValue | int:
        """The crush color (:class:`ColorValue`, or a raw int for non-standard values)."""
        return color_value_from_proto(int(self._info.variation_id))

    @color.setter
    def color(self, value: ColorLike | int) -> None:
        self._info.variation_id = color_to_value(value)

    def with_ctrl(self, *, t: int | PositionLike, x: int, w: int, h: int) -> Self:
        """Return a copy with a control joint appended at the given timing and geometry."""
        copy = self.clone()
        copy.add_ctrl(t=t, x=x, w=w, h=h)
        return copy

    def converted[T: (Slide, AirSlide)](self, target: type[T], **overrides: Any) -> T:
        """Return a new note of type ``target`` carrying this note's geometry and joints."""
        return cast(T, self._converted_to(target, **overrides))

    def to_raw(self, *, skip_validation: bool = False) -> RawNote:
        """Convert to a :class:`RawNote` tree (begin note with joint children)."""
        return self._to_raw_tree(skip_validation=skip_validation)
