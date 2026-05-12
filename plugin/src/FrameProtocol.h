#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "margrete/rpc/v1/messages.pb.h"

class FrameProtocol {
public:
    static constexpr std::uint32_t MaxFrameSize = 16u * 1024u * 1024u;

    static std::vector<std::byte> Encode(const margrete::rpc::v1::Envelope& envelope);
    static margrete::rpc::v1::Envelope Decode(const std::vector<std::byte>& frame);
};
