use crate::error::{PluginError, Result};
use crate::proto::v1::Envelope;
use prost::Message;

pub const MAX_FRAME_SIZE: u32 = 16 * 1024 * 1024;

pub fn encode(envelope: &Envelope) -> Result<Vec<u8>> {
    let payload = envelope.encode_to_vec();
    if payload.len() as u32 > MAX_FRAME_SIZE {
        return Err(PluginError::internal("frame payload is too large"));
    }
    let size = payload.len() as u32;
    let mut frame = Vec::with_capacity(4 + payload.len());
    frame.extend_from_slice(&size.to_le_bytes());
    frame.extend_from_slice(&payload);
    Ok(frame)
}

pub fn decode(frame: &[u8]) -> Result<Envelope> {
    if frame.len() < 4 {
        return Err(PluginError::internal("frame header is truncated"));
    }
    let size = u32::from_le_bytes([frame[0], frame[1], frame[2], frame[3]]);
    if size > MAX_FRAME_SIZE {
        return Err(PluginError::internal("frame payload is too large"));
    }
    if frame.len() - 4 != size as usize {
        return Err(PluginError::internal("frame payload is truncated"));
    }
    Envelope::decode(&frame[4..])
        .map_err(|_| PluginError::internal("frame payload is not a valid protobuf envelope"))
}

pub fn payload_size_from_header(header: &[u8; 4]) -> Result<u32> {
    let size = u32::from_le_bytes(*header);
    if size > MAX_FRAME_SIZE {
        Err(PluginError::internal("frame payload is too large"))
    } else {
        Ok(size)
    }
}
