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

    assert fields_by_name["begin_edit_request"].number == 4
    assert fields_by_name["begin_edit_response"].number == 5
    assert fields_by_name["apply_edit_request"].number == 13
    assert fields_by_name["apply_edit_response"].number == 14
    assert fields_by_name["undo_request"].number == 15
    assert fields_by_name["undo_response"].number == 16
    assert fields_by_name["redo_request"].number == 17
    assert fields_by_name["redo_response"].number == 18
    assert fields_by_name["current_tick_request"].number == 19
    assert fields_by_name["current_tick_response"].number == 20
    assert fields_by_name["status_request"].number == 21
    assert fields_by_name["status_response"].number == 22
    assert fields_by_name["error_response"].number == 12
    assert not OLD_ENVELOPE_BODY_FIELDS.intersection(fields_by_name)


def test_begin_edit_request_and_response_have_scan_field():
    request = messages_pb2.BeginEditRequest(name="edit", scan=False)
    response = messages_pb2.BeginEditResponse(current_tick=480, scan=False)

    assert request.scan is False
    assert response.scan is False


def test_begin_edit_scan_fields_use_expected_numbers():
    assert messages_pb2.BeginEditRequest.DESCRIPTOR.fields_by_name["scan"].number == 4
    assert messages_pb2.BeginEditResponse.DESCRIPTOR.fields_by_name["scan"].number == 9


def test_begin_edit_event_scan_note_til_only_field_numbers():
    assert (
        messages_pb2.BeginEditRequest.DESCRIPTOR.fields_by_name["event_scan_note_til_only"].number
        == 5
    )
    assert (
        messages_pb2.BeginEditResponse.DESCRIPTOR.fields_by_name["event_scan_note_til_only"].number
        == 10
    )


def test_air_crush_color_wire_values_are_named_enum():
    assert messages_pb2.AIR_CRUSH_COLOR_DEFAULT == 0
    assert messages_pb2.AIR_CRUSH_COLOR_RED == 1
    assert messages_pb2.AIR_CRUSH_COLOR_ORANGE == 2
    assert messages_pb2.AIR_CRUSH_COLOR_YELLOW == 3
    assert messages_pb2.AIR_CRUSH_COLOR_GREEN == 4
    assert messages_pb2.AIR_CRUSH_COLOR_SKY == 5
    assert messages_pb2.AIR_CRUSH_COLOR_BLUE == 6
    assert messages_pb2.AIR_CRUSH_COLOR_VIOLET == 7
    assert messages_pb2.AIR_CRUSH_COLOR_PINK == 8
    assert messages_pb2.AIR_CRUSH_COLOR_WHITE == 10
    assert messages_pb2.AIR_CRUSH_COLOR_BLACK == 11
    assert messages_pb2.AIR_CRUSH_COLOR_GRASS == 12
    assert messages_pb2.AIR_CRUSH_COLOR_SKY_BLUE == 13
    assert messages_pb2.AIR_CRUSH_COLOR_COBALT_BLUE == 14
    assert messages_pb2.AIR_CRUSH_COLOR_PURPLE == 15
    assert messages_pb2.AIR_CRUSH_COLOR_NONE == 35

    field = messages_pb2.Note.DESCRIPTOR.fields_by_name["variation_id"]
    assert field.enum_type is messages_pb2.AirCrushColor.DESCRIPTOR
