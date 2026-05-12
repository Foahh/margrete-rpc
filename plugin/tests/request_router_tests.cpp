#include <catch2/catch_test_macros.hpp>

#include "FakeMargrete.h"
#include "RequestRouter.h"
#include "margrete/rpc/v1/messages.pb.h"

TEST_CASE("router responds to ping")
{
    FakeContext context;
    RequestRouter router(&context);
    margrete::rpc::v1::Envelope request;
    request.set_request_id(11);
    request.mutable_ping_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 11);
    REQUIRE(response.has_ping_response());
    REQUIRE(response.ping_response().server_name() == "Margrete RPC");
}

TEST_CASE("router responds to current tick")
{
    FakeContext context;
    context.currentTick = 1234;
    RequestRouter router(&context);
    margrete::rpc::v1::Envelope request;
    request.set_request_id(12);
    request.mutable_get_current_tick_request();

    const auto response = router.route(request);

    REQUIRE(response.get_current_tick_response().tick() == 1234);
}

TEST_CASE("router maps bad append to error response")
{
    FakeContext context;
    RequestRouter router(&context);
    margrete::rpc::v1::Envelope request;
    request.set_request_id(13);
    request.mutable_append_transaction_request()->set_transaction_name("empty");

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 13);
    REQUIRE(response.has_error_response());
    REQUIRE(response.error_response().code() == margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT);
}
