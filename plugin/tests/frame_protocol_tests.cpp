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
