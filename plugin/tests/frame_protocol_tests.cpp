#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include "FrameProtocol.h"
#include "margrete/rpc/v1/messages.pb.h"

using Catch::Matchers::ContainsSubstring;

TEST_CASE("frame protocol round trips envelope")
{
    margrete::rpc::v1::Envelope envelope;
    envelope.set_request_id(42);
    envelope.mutable_ping_request();

    const std::vector<std::byte> frame = FrameProtocol::Encode(envelope);
    const margrete::rpc::v1::Envelope decoded = FrameProtocol::Decode(frame);

    REQUIRE(decoded.request_id() == 42);
    REQUIRE(decoded.has_ping_request());
}

TEST_CASE("frame protocol rejects truncated payload")
{
    const std::vector<std::byte> frame{std::byte{4}, std::byte{0}, std::byte{0}, std::byte{0}, std::byte{'a'}};

    REQUIRE_THROWS_WITH(FrameProtocol::Decode(frame), ContainsSubstring("frame payload is truncated"));
}

TEST_CASE("frame protocol round trips empty payload")
{
    const std::vector<std::byte> frame{std::byte{0}, std::byte{0}, std::byte{0}, std::byte{0}};
    const auto decoded = FrameProtocol::Decode(frame);
    REQUIRE(decoded.request_id() == 0);
    REQUIRE_FALSE(decoded.has_ping_request());
}

TEST_CASE("frame protocol rejects oversized header")
{
    const std::uint32_t tooBig = FrameProtocol::MaxFrameSize + 1u; // 0x01000001
    const std::vector<std::byte> frame{
        static_cast<std::byte>(tooBig & 0xff), static_cast<std::byte>((tooBig >> 8) & 0xff),
        static_cast<std::byte>((tooBig >> 16) & 0xff), static_cast<std::byte>((tooBig >> 24) & 0xff)};
    REQUIRE_THROWS_WITH(FrameProtocol::Decode(frame), ContainsSubstring("frame payload is too large"));
}

TEST_CASE("frame protocol rejects invalid protobuf payload")
{
    // size = 1, payload = 0x08 (field 1, varint tag) with no following value -> parse fails
    const std::vector<std::byte> frame{std::byte{1}, std::byte{0}, std::byte{0}, std::byte{0}, std::byte{0x08}};
    REQUIRE_THROWS_WITH(FrameProtocol::Decode(frame), ContainsSubstring("not a valid protobuf envelope"));
}
