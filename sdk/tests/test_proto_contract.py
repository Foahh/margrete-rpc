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
        "error_response",
    ]

    assert fields_by_name["begin_edit_request"].number == 4
    assert fields_by_name["begin_edit_response"].number == 5
    assert fields_by_name["apply_edit_request"].number == 13
    assert fields_by_name["apply_edit_response"].number == 14
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
