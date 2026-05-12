#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include "FakeMargrete.h"
#include "TransactionApplier.h"
#include "margrete/rpc/v1/messages.pb.h"

using Catch::Matchers::ContainsSubstring;

TEST_CASE("empty transaction is rejected") {
    FakeContext context;
    TransactionApplier applier;
    margrete::rpc::v1::AppendTransactionRequest request;
    request.set_transaction_name("empty");

    REQUIRE_THROWS_WITH(applier.apply(context, request), ContainsSubstring("transaction is empty"));
}

TEST_CASE("tap transaction commits one undo recording") {
    FakeContext context;
    TransactionApplier applier;
    margrete::rpc::v1::AppendTransactionRequest request;
    request.set_transaction_name("tap");
    auto* item = request.add_items();
    auto* tap = item->mutable_note()->mutable_tap();
    tap->mutable_base()->set_tick(120);
    tap->mutable_base()->set_lane(4);
    tap->mutable_base()->set_width(1);

    const std::uint32_t count = applier.apply(context, request);

    REQUIRE(count == 1);
    REQUIRE(context.undo.beginCount == 1);
    REQUIRE(context.undo.commitCount == 1);
    REQUIRE(context.undo.discardCount == 0);
    REQUIRE(context.chart.appendedNotes == 1);
    REQUIRE(context.updated);
}
