use margrete_rpc::rpc::framing::{self, MAX_FRAME_SIZE};
use margrete_rpc::rpc::proto::{envelope, Envelope, PingRequest};

#[test]
fn frame_protocol_round_trips_envelope() {
    let envelope = Envelope {
        request_id: 42,
        body: Some(envelope::Body::PingRequest(PingRequest {})),
    };
    let frame = framing::encode(&envelope).unwrap();
    let decoded = framing::decode(&frame).unwrap();
    assert_eq!(decoded.request_id, 42);
    assert!(matches!(decoded.body, Some(envelope::Body::PingRequest(_))));
}

#[test]
fn frame_protocol_rejects_truncated_payload() {
    let frame = [4, 0, 0, 0, b'a'];
    let err = framing::decode(&frame).unwrap_err().to_string();
    assert!(err.contains("frame payload is truncated"));
}

#[test]
fn frame_protocol_round_trips_empty_payload() {
    let frame = [0, 0, 0, 0];
    let decoded = framing::decode(&frame).unwrap();
    assert_eq!(decoded.request_id, 0);
    assert!(!matches!(
        decoded.body,
        Some(envelope::Body::PingRequest(_))
    ));
}

#[test]
fn frame_protocol_rejects_oversized_header() {
    let too_big = MAX_FRAME_SIZE + 1;
    let frame = too_big.to_le_bytes();
    let err = framing::decode(&frame).unwrap_err().to_string();
    assert!(err.contains("frame payload is too large"));
}

#[test]
fn frame_protocol_rejects_invalid_protobuf_payload() {
    let frame = [1, 0, 0, 0, 0x08];
    let err = framing::decode(&frame).unwrap_err().to_string();
    assert!(err.contains("not a valid protobuf envelope"));
}
