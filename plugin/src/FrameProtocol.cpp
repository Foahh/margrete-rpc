#include "FrameProtocol.h"

#include <stdexcept>
#include <string>

std::vector<std::byte> FrameProtocol::Encode(const margrete::rpc::v1::Envelope& envelope) {
    const std::string payload = envelope.SerializeAsString();
    if (payload.size() > MaxFrameSize) {
        throw std::runtime_error("frame payload is too large");
    }

    std::vector<std::byte> frame(4 + payload.size());
    const auto size = static_cast<std::uint32_t>(payload.size());
    frame[0] = static_cast<std::byte>(size & 0xff);
    frame[1] = static_cast<std::byte>((size >> 8) & 0xff);
    frame[2] = static_cast<std::byte>((size >> 16) & 0xff);
    frame[3] = static_cast<std::byte>((size >> 24) & 0xff);
    for (std::size_t i = 0; i < payload.size(); ++i) {
        frame[4 + i] = static_cast<std::byte>(payload[i]);
    }
    return frame;
}

margrete::rpc::v1::Envelope FrameProtocol::Decode(const std::vector<std::byte>& frame) {
    if (frame.size() < 4) {
        throw std::runtime_error("frame header is truncated");
    }
    const auto size = static_cast<std::uint32_t>(frame[0]) |
                       (static_cast<std::uint32_t>(frame[1]) << 8) |
                       (static_cast<std::uint32_t>(frame[2]) << 16) |
                       (static_cast<std::uint32_t>(frame[3]) << 24);
    if (size > MaxFrameSize) {
        throw std::runtime_error("frame payload is too large");
    }
    if (frame.size() - 4 != size) {
        throw std::runtime_error("frame payload is truncated");
    }

    std::string payload;
    payload.resize(size);
    for (std::size_t i = 0; i < size; ++i) {
        payload[i] = static_cast<char>(frame[4 + i]);
    }

    margrete::rpc::v1::Envelope envelope;
    if (!envelope.ParseFromString(payload)) {
        throw std::runtime_error("frame payload is not a valid protobuf envelope");
    }
    return envelope;
}
