from __future__ import annotations

from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
from enum import IntEnum
from fractions import Fraction

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

_TICKS_PER_BEAT = 1920


class NoteType(IntEnum):
    UNKNOWN = messages_pb2.NOTE_TYPE_UNKNOWN
    TAP = messages_pb2.NOTE_TYPE_TAP
    EXTAP = messages_pb2.NOTE_TYPE_EXTAP
    FLICK = messages_pb2.NOTE_TYPE_FLICK
    DAMAGE = messages_pb2.NOTE_TYPE_DAMAGE
    HOLD = messages_pb2.NOTE_TYPE_HOLD
    SLIDE = messages_pb2.NOTE_TYPE_SLIDE
    AIR = messages_pb2.NOTE_TYPE_AIR
    AIRHOLD = messages_pb2.NOTE_TYPE_AIRHOLD
    AIRSLIDE = messages_pb2.NOTE_TYPE_AIRSLIDE
    AIRCRUSH = messages_pb2.NOTE_TYPE_AIRCRUSH
    CLICK = messages_pb2.NOTE_TYPE_CLICK


class LongAttr(IntEnum):
    NONE = messages_pb2.LONG_ATTR_NONE
    BEGIN = messages_pb2.LONG_ATTR_BEGIN
    STEP = messages_pb2.LONG_ATTR_STEP
    CONTROL = messages_pb2.LONG_ATTR_CONTROL
    CURVE_CONTROL = messages_pb2.LONG_ATTR_CURVE_CONTROL
    END = messages_pb2.LONG_ATTR_END
    END_NOACT = messages_pb2.LONG_ATTR_END_NOACT


class Direction(IntEnum):
    NONE = messages_pb2.DIRECTION_NONE
    AUTO = messages_pb2.DIRECTION_AUTO
    UP = messages_pb2.DIRECTION_UP
    DOWN = messages_pb2.DIRECTION_DOWN
    CENTER = messages_pb2.DIRECTION_CENTER
    LEFT = messages_pb2.DIRECTION_LEFT
    RIGHT = messages_pb2.DIRECTION_RIGHT
    UPLEFT = messages_pb2.DIRECTION_UPLEFT
    UPRIGHT = messages_pb2.DIRECTION_UPRIGHT
    DOWNLEFT = messages_pb2.DIRECTION_DOWNLEFT
    DOWNRIGHT = messages_pb2.DIRECTION_DOWNRIGHT
    ROTATE_LEFT = messages_pb2.DIRECTION_ROTATE_LEFT
    ROTATE_RIGHT = messages_pb2.DIRECTION_ROTATE_RIGHT
    INOUT = messages_pb2.DIRECTION_INOUT
    OUTIN = messages_pb2.DIRECTION_OUTIN


class ExAttr(IntEnum):
    NONE = messages_pb2.EX_ATTR_NONE
    INVERT = messages_pb2.EX_ATTR_INVERT
    HAS_NOTE = messages_pb2.EX_ATTR_HAS_NOTE
    EXJDG = messages_pb2.EX_ATTR_EXJDG


class AirCrushOption(IntEnum):
    TRACELIKE = 0
    HEAD_ONLY = 0x7FFFFFFF


@dataclass
class Note:
    type: NoteType = NoteType.UNKNOWN
    long_attr: LongAttr = LongAttr.NONE
    direction: Direction = Direction.NONE
    ex_attr: ExAttr = ExAttr.NONE
    variation_id: int = 0
    x: int = 0
    width: int = 0
    height: int = 0
    tick: int = 0
    timeline_id: int = 0
    option_value: int = 0
    _: KW_ONLY
    children: list[Note] = field(default_factory=list)
    id: int | None = None

    @classmethod
    def tap(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls(type=NoteType.TAP, tick=tick, x=x, width=width, height=height, **kwargs)

    @property
    def bar(self) -> tuple[int, int]:
        fraction = Fraction(self.tick, _TICKS_PER_BEAT)
        return fraction.numerator, fraction.denominator

    @bar.setter
    def bar(self, value: tuple[int, int]) -> None:
        numerator, denominator = value
        tick = Fraction(numerator * _TICKS_PER_BEAT, denominator)
        if tick.denominator != 1:
            raise ValueError("beat division must resolve to a whole tick")
        self.tick = tick.numerator

    @classmethod
    def extap(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls(type=NoteType.EXTAP, tick=tick, x=x, width=width, height=height, **kwargs)

    @classmethod
    def flick(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls(type=NoteType.FLICK, tick=tick, x=x, width=width, height=height, **kwargs)

    @classmethod
    def damage(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls(type=NoteType.DAMAGE, tick=tick, x=x, width=width, height=height, **kwargs)

    @classmethod
    def hold_begin(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls._long_segment(NoteType.HOLD, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @classmethod
    def hold_end(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls._long_segment(NoteType.HOLD, LongAttr.END, tick, x, width, height, **kwargs)

    @classmethod
    def slide_begin(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls._slide_segment(NoteType.SLIDE, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @classmethod
    def slide_step(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls._slide_segment(NoteType.SLIDE, LongAttr.STEP, tick, x, width, height, **kwargs)

    @classmethod
    def slide_control(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls._slide_segment(
            NoteType.SLIDE, LongAttr.CONTROL, tick, x, width, height, **kwargs
        )

    @classmethod
    def slide_curve_control(
        cls,
        tick: int,
        x: int,
        width: int,
        *,
        height: int = 800,
        **kwargs,
    ) -> Note:
        return cls._slide_segment(
            NoteType.SLIDE,
            LongAttr.CURVE_CONTROL,
            tick,
            x,
            width,
            height,
            **kwargs,
        )

    @classmethod
    def slide_end(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls._slide_segment(NoteType.SLIDE, LongAttr.END, tick, x, width, height, **kwargs)

    @classmethod
    def air(cls, tick: int, x: int, width: int, *, height: int = 800, **kwargs) -> Note:
        return cls(type=NoteType.AIR, tick=tick, x=x, width=width, height=height, **kwargs)

    @classmethod
    def with_air(cls, host: Note, *air_notes: Note) -> Note:
        if not air_notes:
            air_notes = (cls.air(host.tick, host.x, host.width, height=host.height),)
        host.children.extend(air_notes)
        return host

    @classmethod
    def air_slide_begin(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._slide_segment(
            NoteType.AIRSLIDE, LongAttr.BEGIN, tick, x, width, height, **kwargs
        )

    @classmethod
    def air_slide_step(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._slide_segment(
            NoteType.AIRSLIDE, LongAttr.STEP, tick, x, width, height, **kwargs
        )

    @classmethod
    def air_slide_control(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._slide_segment(
            NoteType.AIRSLIDE, LongAttr.CONTROL, tick, x, width, height, **kwargs
        )

    @classmethod
    def air_slide_curve_control(
        cls,
        tick: int,
        x: int,
        width: int,
        height: int,
        **kwargs,
    ) -> Note:
        return cls._slide_segment(
            NoteType.AIRSLIDE,
            LongAttr.CURVE_CONTROL,
            tick,
            x,
            width,
            height,
            **kwargs,
        )

    @classmethod
    def air_slide_end(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._slide_segment(NoteType.AIRSLIDE, LongAttr.END, tick, x, width, height, **kwargs)

    @classmethod
    def air_slide_end_noact(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._slide_segment(
            NoteType.AIRSLIDE,
            LongAttr.END_NOACT,
            tick,
            x,
            width,
            height,
            **kwargs,
        )

    @classmethod
    def _slide_segment(
        cls,
        note_type: NoteType,
        long_attr: LongAttr,
        tick: int,
        x: int,
        width: int,
        height: int,
        **kwargs,
    ) -> Note:
        return cls(
            type=note_type,
            tick=tick,
            x=x,
            width=width,
            height=height,
            long_attr=long_attr,
            **kwargs,
        )

    @classmethod
    def _long_segment(
        cls,
        note_type: NoteType,
        long_attr: LongAttr,
        tick: int,
        x: int,
        width: int,
        height: int,
        **kwargs,
    ) -> Note:
        return cls(
            type=note_type,
            tick=tick,
            x=x,
            width=width,
            height=height,
            long_attr=long_attr,
            **kwargs,
        )

    @classmethod
    def _long_note_tree(
        cls,
        factory_name: str,
        note_type: NoteType,
        nodes: tuple[Note, ...],
    ) -> Note:
        if not nodes:
            raise TypeError(f"Note.{factory_name}() requires at least one node")
        for node in nodes:
            if not isinstance(node, Note):
                raise TypeError(f"Note.{factory_name}() accepts Note nodes only")
            if node.type is not note_type:
                raise TypeError(f"Note.{factory_name}() requires {note_type.name} nodes")
        root = nodes[0]
        if root.long_attr is not LongAttr.BEGIN:
            raise ValueError(f"Note.{factory_name}() first node must be a BEGIN segment")
        root.children = list(nodes[1:])
        return root

    @classmethod
    def air_hold_begin(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._long_segment(NoteType.AIRHOLD, LongAttr.BEGIN, tick, x, width, height, **kwargs)

    @classmethod
    def air_hold_step(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._long_segment(NoteType.AIRHOLD, LongAttr.STEP, tick, x, width, height, **kwargs)

    @classmethod
    def air_hold_end(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._long_segment(NoteType.AIRHOLD, LongAttr.END, tick, x, width, height, **kwargs)

    @classmethod
    def air_hold_end_noact(cls, tick: int, x: int, width: int, height: int, **kwargs) -> Note:
        return cls._long_segment(
            NoteType.AIRHOLD,
            LongAttr.END_NOACT,
            tick,
            x,
            width,
            height,
            **kwargs,
        )

    @classmethod
    def _air_crush_segment(
        cls,
        long_attr: LongAttr,
        tick: int,
        x: int,
        width: int,
        height: int,
        option_value: int,
        **kwargs,
    ) -> Note:
        return cls(
            type=NoteType.AIRCRUSH,
            tick=tick,
            x=x,
            width=width,
            height=height,
            long_attr=long_attr,
            option_value=int(option_value),
            **kwargs,
        )

    @classmethod
    def air_crush_begin(
        cls,
        tick: int,
        x: int,
        width: int,
        height: int,
        option_value: int,
        **kwargs,
    ) -> Note:
        return cls._air_crush_segment(
            LongAttr.BEGIN,
            tick,
            x,
            width,
            height,
            int(option_value),
            **kwargs,
        )

    @classmethod
    def air_crush_control(
        cls,
        tick: int,
        x: int,
        width: int,
        height: int,
        option_value: int,
        **kwargs,
    ) -> Note:
        return cls._air_crush_segment(
            LongAttr.CONTROL,
            tick,
            x,
            width,
            height,
            option_value,
            **kwargs,
        )

    @classmethod
    def air_crush_end(
        cls,
        tick: int,
        x: int,
        width: int,
        height: int,
        option_value: int,
        **kwargs,
    ) -> Note:
        return cls._air_crush_segment(LongAttr.END, tick, x, width, height, option_value, **kwargs)

    @classmethod
    def from_proto(cls, proto: messages_pb2.Note) -> Note:
        return cls(
            id=proto.id if proto.HasField("id") else None,
            type=NoteType(proto.type),
            long_attr=LongAttr(proto.long_attr),
            direction=Direction(proto.direction),
            ex_attr=ExAttr(proto.ex_attr),
            variation_id=proto.variation_id,
            x=proto.x,
            width=proto.width,
            height=proto.height,
            tick=proto.tick,
            timeline_id=proto.timeline_id,
            option_value=proto.option_value,
            children=[cls.from_proto(child) for child in proto.children],
        )

    def to_proto(self) -> messages_pb2.Note:
        proto = messages_pb2.Note(
            type=int(self.type),
            long_attr=int(self.long_attr),
            direction=int(self.direction),
            ex_attr=int(self.ex_attr),
            variation_id=self.variation_id,
            x=self.x,
            width=self.width,
            height=self.height,
            tick=self.tick,
            timeline_id=self.timeline_id,
            option_value=self.option_value,
        )
        if self.id is not None:
            proto.id = self.id
        proto.children.extend(child.to_proto() for child in self.children)
        return proto


class _LongNoteTreeFactory:
    __slots__ = ("_factory_name", "_note_type", "begin")

    def __init__(
        self,
        factory_name: str,
        note_type: NoteType,
        begin: Callable[..., Note],
    ) -> None:
        self._factory_name = factory_name
        self._note_type = note_type
        self.begin = begin

    def __call__(self, *nodes: Note) -> Note:
        return Note._long_note_tree(self._factory_name, self._note_type, nodes)


Note.hold = _LongNoteTreeFactory("hold", NoteType.HOLD, Note.hold_begin)
Note.slide = _LongNoteTreeFactory("slide", NoteType.SLIDE, Note.slide_begin)
Note.air_slide = _LongNoteTreeFactory("air_slide", NoteType.AIRSLIDE, Note.air_slide_begin)
Note.air_hold = _LongNoteTreeFactory("air_hold", NoteType.AIRHOLD, Note.air_hold_begin)
Note.air_crush = _LongNoteTreeFactory("air_crush", NoteType.AIRCRUSH, Note.air_crush_begin)
