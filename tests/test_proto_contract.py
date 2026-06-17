from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2

OLD_ENVELOPE_BODY_FIELDS = {
    "begin_append_request",
    "begin_append_response",
    "apply_edit_patch_request",
    "apply_edit_patch_response",
    "apply_edit_delta_request",
    "apply_edit_delta_response",
    "apply_append_patch_request",
    "apply_append_patch_response",
}


def test_edit_wire_contract_has_only_begin_and_apply_edit():
    assert hasattr(messages_pb2, "BeginEditRequest")
    assert hasattr(messages_pb2, "BeginEditResponse")
    assert hasattr(messages_pb2, "ApplyEditRequest")
    assert hasattr(messages_pb2, "ApplyEditResponse")
    assert hasattr(messages_pb2, "UndoRequest")
    assert hasattr(messages_pb2, "UndoResponse")
    assert hasattr(messages_pb2, "RedoRequest")
    assert hasattr(messages_pb2, "RedoResponse")
    assert hasattr(messages_pb2, "CurrentTickRequest")
    assert hasattr(messages_pb2, "CurrentTickResponse")
    assert hasattr(messages_pb2, "StatusRequest")
    assert hasattr(messages_pb2, "StatusResponse")

    assert not hasattr(messages_pb2, "BeginAppendRequest")
    assert not hasattr(messages_pb2, "BeginAppendResponse")
    assert not hasattr(messages_pb2, "ApplyEditPatchRequest")
    assert not hasattr(messages_pb2, "ApplyEditPatchResponse")
    assert not hasattr(messages_pb2, "ApplyEditDeltaRequest")
    assert not hasattr(messages_pb2, "ApplyEditDeltaResponse")
    assert not hasattr(messages_pb2, "ApplyAppendPatchRequest")
    assert not hasattr(messages_pb2, "ApplyAppendPatchResponse")


def test_envelope_body_contract_uses_expected_fields_and_numbers():
    body = messages_pb2.Envelope.DESCRIPTOR.oneofs_by_name["body"]
    fields_by_name = messages_pb2.Envelope.DESCRIPTOR.fields_by_name

    assert [field.name for field in body.fields] == [
        "ping_request",
        "ping_response",
        "begin_edit_request",
        "begin_edit_response",
        "apply_edit_request",
        "apply_edit_response",
        "undo_request",
        "undo_response",
        "redo_request",
        "redo_response",
        "current_tick_request",
        "current_tick_response",
        "status_request",
        "status_response",
        "error_response",
    ]

    assert [field.number for field in body.fields] == list(range(2, 17))
    assert not OLD_ENVELOPE_BODY_FIELDS.intersection(fields_by_name)


def test_begin_edit_request_and_response_have_snapshot_field():
    request = messages_pb2.BeginEditRequest(snapshot=False)
    response = messages_pb2.BeginEditResponse(current_tick=480, snapshot=False)

    assert request.snapshot is False
    assert response.snapshot is False


def test_status_response_has_api_version_field():
    response = messages_pb2.StatusResponse(api_version=1)

    assert response.api_version == 1
    assert messages_pb2.StatusResponse.DESCRIPTOR.fields_by_name["api_version"].number == 9


def test_begin_edit_snapshot_fields_use_expected_numbers():
    assert (
        messages_pb2.BeginEditRequest.DESCRIPTOR.fields_by_name["event_scan_lookahead_ticks"].number
        == 1
    )
    assert messages_pb2.BeginEditRequest.DESCRIPTOR.fields_by_name["event_scan_til_ids"].number == 2
    assert messages_pb2.BeginEditRequest.DESCRIPTOR.fields_by_name["snapshot"].number == 3
    assert messages_pb2.BeginEditResponse.DESCRIPTOR.fields_by_name["snapshot"].number == 9


def test_begin_edit_event_scan_til_ids_is_wrapper_message():
    field = messages_pb2.BeginEditRequest.DESCRIPTOR.fields_by_name["event_scan_til_ids"]
    assert field.number == 2
    assert field.message_type.name == "EventScanTilIds"
    assert field.has_presence is True


def test_apply_edit_request_fields_are_sequential():
    fields = messages_pb2.ApplyEditRequest.DESCRIPTOR.fields
    assert [field.name for field in fields] == [
        "replace_all_notes",
        "notes_upsert",
        "note_ids_delete",
        "bpm_upsert",
        "beat_upsert",
        "til_upsert",
        "note_speed_upsert",
        "bpm_ticks_delete",
        "beat_bars_delete",
        "til_keys_delete",
        "note_speed_ticks_delete",
    ]
    assert [field.number for field in fields] == list(range(1, 12))


def test_air_crush_color_wire_values_are_named_enum():
    assert messages_pb2.COLOR_DEFAULT == 0
    assert messages_pb2.COLOR_RED == 1
    assert messages_pb2.COLOR_ORANGE == 2
    assert messages_pb2.COLOR_YELLOW == 3
    assert messages_pb2.COLOR_GREEN == 4
    assert messages_pb2.COLOR_SKY == 5
    assert messages_pb2.COLOR_BLUE == 6
    assert messages_pb2.COLOR_VIOLET == 7
    assert messages_pb2.COLOR_PINK == 8
    assert messages_pb2.COLOR_WHITE == 10
    assert messages_pb2.COLOR_BLACK == 11
    assert messages_pb2.COLOR_GRASS == 12
    assert messages_pb2.COLOR_SKY_BLUE == 13
    assert messages_pb2.COLOR_COBALT_BLUE == 14
    assert messages_pb2.COLOR_PURPLE == 15
    assert messages_pb2.COLOR_NONE == 35

    field = messages_pb2.Note.DESCRIPTOR.fields_by_name["variation_id"]
    assert field.enum_type is messages_pb2.Color.DESCRIPTOR
