import pytest

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import AirHold, AirSlide, AirSlidePoint, Hold, RawNoteNode, Tap


def test_tap_converts_to_note_object():
    item = Tap(tick=120, lane=4, width=1).to_append_item()

    assert item.note.tap.base.tick == 120
    assert item.note.tap.base.lane == 4
    assert item.note.tap.base.width == 1


def test_hold_rejects_negative_duration():
    with pytest.raises(ValueError, match="duration"):
        Hold(tick=120, lane=4, width=2, duration=-1).to_append_item()


def test_air_hold_converts_to_note_object():
    item = AirHold(tick=10, lane=2, width=1, duration=120, height=64).to_append_item()

    assert item.note.air_hold.base.tick == 10
    assert item.note.air_hold.duration == 120
    assert item.note.air_hold.height == 64


def test_air_slide_converts_points():
    item = AirSlide(
        tick=100,
        lane=3,
        width=4,
        points=[
            AirSlidePoint(dt=0, lane=3, height=80),
            AirSlidePoint(dt=480, lane=8, height=180),
        ],
    ).to_append_item()

    assert item.note.air_slide.base.tick == 100
    assert item.note.air_slide.points[1].dt == 480
    assert item.note.air_slide.points[1].height == 180


def test_raw_note_node_converts_children():
    raw = RawNoteNode(
        type=messages_pb2.NOTE_TYPE_SLIDE,
        long_attr=messages_pb2.LONG_ATTR_BEGIN,
        x=4,
        width=2,
        tick=100,
        children=[
            RawNoteNode(
                type=messages_pb2.NOTE_TYPE_SLIDE,
                long_attr=messages_pb2.LONG_ATTR_END,
                x=6,
                width=2,
                tick=580,
            )
        ],
    )

    item = raw.to_append_item()

    assert item.raw_note.type == messages_pb2.NOTE_TYPE_SLIDE
    assert item.raw_note.children[0].long_attr == messages_pb2.LONG_ATTR_END
