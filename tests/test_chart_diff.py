import pytest

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import Chart
from margrete_rpc.chart.diff import build_apply_edit_request, capture_edit_snapshot
from margrete_rpc.chart.notes import R, RawNote


def _id_note(note_id, *, x=1, w=2, tick=0):
    proto = messages_pb2.Note(id=note_id, type=messages_pb2.NOTE_TYPE_TAP, tick=tick, x=x, width=w)
    return RawNote.from_proto(proto)


def test_scan_noop_returns_none():
    chart = Chart(notes=[_id_note(1)])
    snap = capture_edit_snapshot(chart)
    final = Chart(notes=[_id_note(1)])
    req = build_apply_edit_request("e", final, scan=True, replace_all_notes=False, snapshot=snap)
    assert req is None


def test_scan_modified_note_upserts_with_id():
    snap = capture_edit_snapshot(Chart(notes=[_id_note(1, x=1)]))
    final = Chart(notes=[_id_note(1, x=5)])
    req = build_apply_edit_request("e", final, scan=True, replace_all_notes=False, snapshot=snap)
    assert req is not None
    assert len(req.notes_upsert) == 1
    assert req.notes_upsert[0].id == 1
    assert req.notes_upsert[0].x == 5
    assert list(req.note_ids_delete) == []


def test_scan_deleted_note_emits_delete():
    snap = capture_edit_snapshot(Chart(notes=[_id_note(1), _id_note(2, x=3)]))
    final = Chart(notes=[_id_note(1)])
    req = build_apply_edit_request("e", final, scan=True, replace_all_notes=False, snapshot=snap)
    assert req is not None
    assert list(req.note_ids_delete) == [2]
    assert len(req.notes_upsert) == 0


def test_scan_added_note_upserts_without_id():
    snap = capture_edit_snapshot(Chart(notes=[_id_note(1)]))
    final = Chart(notes=[_id_note(1), R.tap(t=0, x=7, w=2)])
    req = build_apply_edit_request("e", final, scan=True, replace_all_notes=False, snapshot=snap)
    assert req is not None
    assert len(req.notes_upsert) == 1
    assert req.notes_upsert[0].HasField("id") is False
    assert req.notes_upsert[0].x == 7
    assert list(req.note_ids_delete) == []


def test_replace_all_strips_ids():
    chart = Chart(notes=[_id_note(1)])
    req = build_apply_edit_request("e", chart, scan=False, replace_all_notes=True, snapshot=None)
    assert req is not None
    assert req.replace_all_notes is True
    assert len(req.notes_upsert) == 1
    assert req.notes_upsert[0].HasField("id") is False


def test_scan_false_with_existing_id_raises():
    chart = Chart(notes=[_id_note(1)])
    with pytest.raises(ValueError):
        build_apply_edit_request("e", chart, scan=False, replace_all_notes=False, snapshot=None)


def test_scan_child_structure_change_deletes_and_recreates():
    orig_root = messages_pb2.Note(
        id=1,
        type=messages_pb2.NOTE_TYPE_HOLD,
        long_attr=messages_pb2.LONG_ATTR_BEGIN,
        tick=0,
        x=1,
        width=2,
    )
    orig_root.children.add(
        id=2,
        type=messages_pb2.NOTE_TYPE_HOLD,
        long_attr=messages_pb2.LONG_ATTR_END,
        tick=480,
        x=1,
        width=2,
    )
    final_root = messages_pb2.Note(
        id=1,
        type=messages_pb2.NOTE_TYPE_HOLD,
        long_attr=messages_pb2.LONG_ATTR_BEGIN,
        tick=0,
        x=1,
        width=2,
    )
    final_root.children.add(  # no id on the child this time, AND a moved x (1 -> 5)
        type=messages_pb2.NOTE_TYPE_HOLD,
        long_attr=messages_pb2.LONG_ATTR_END,
        tick=480,
        x=5,
        width=2,
    )
    snap = capture_edit_snapshot(Chart(notes=[RawNote.from_proto(orig_root)]))
    final = Chart(notes=[RawNote.from_proto(final_root)])
    req = build_apply_edit_request("e", final, scan=True, replace_all_notes=False, snapshot=snap)
    assert req is not None
    assert list(req.note_ids_delete) == [1]
    assert len(req.notes_upsert) == 1
    assert req.notes_upsert[0].HasField("id") is False
