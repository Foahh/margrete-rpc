#include <catch2/catch_test_macros.hpp>

#include "Config.h"
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

TEST_CASE("router retains context while it may be used by background requests")
{
    FakeContext first;
    FakeContext second;
    REQUIRE(first.refCountValue() == 1);
    REQUIRE(second.refCountValue() == 1);

    {
        RequestRouter router(&first);
        REQUIRE(first.refCountValue() == 2);

        router.setContext(&second);
        REQUIRE(first.refCountValue() == 1);
        REQUIRE(second.refCountValue() == 2);

        router.setContext(nullptr);
        REQUIRE(second.refCountValue() == 1);
    }

    REQUIRE(first.refCountValue() == 1);
    REQUIRE(second.refCountValue() == 1);
}

TEST_CASE("router rejects unknown request body")
{
    FakeContext context;
    RequestRouter router(&context);
    margrete::rpc::v1::Envelope request;
    request.set_request_id(13);
    // No oneof field set.

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 13);
    REQUIRE(response.has_error_response());
    REQUIRE(response.error_response().code() == margrete::rpc::v1::ERROR_CODE_INVALID_ARGUMENT);
}

TEST_CASE("router begins edit transaction with note snapshot")
{
    FakeContext context;
    context.currentTick = 777;
    context.chart.addExistingNote(10)->info.tick = 123;
    context.chart.addExistingBpmEvent(200, 180.0);
    RequestRouter router(&context);
    margrete::rpc::v1::Envelope request;
    request.set_request_id(20);
    auto *begin = request.mutable_begin_edit_request();
    begin->set_name("edit");
    begin->set_scan(true);

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 20);
    REQUIRE(response.has_begin_edit_response());
    REQUIRE(response.begin_edit_response().current_tick() == 777);
    REQUIRE(response.begin_edit_response().scan() == true);
    REQUIRE(response.begin_edit_response().notes_size() == 1);
    REQUIRE(response.begin_edit_response().notes(0).id() == 10);
    REQUIRE(response.begin_edit_response().event_scan_extra_tick() == 19200);
    REQUIRE(response.begin_edit_response().event_scan_til_size() == 16);
    REQUIRE(response.begin_edit_response().bpm_events_size() == 1);
    REQUIRE(response.begin_edit_response().bpm_events(0).tick() == 200);
}

TEST_CASE("router begins edit transaction without scan")
{
    FakeContext context;
    context.currentTick = 777;
    context.chart.addExistingNote(10)->info.tick = 123;
    context.chart.addExistingBpmEvent(200, 180.0);
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(23);
    auto *begin = request.mutable_begin_edit_request();
    begin->set_name("append style");
    begin->set_scan(false);

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 23);
    REQUIRE(response.has_begin_edit_response());
    REQUIRE(response.begin_edit_response().current_tick() == 777);
    REQUIRE(response.begin_edit_response().scan() == false);
    REQUIRE(response.begin_edit_response().notes_size() == 0);
    REQUIRE(response.begin_edit_response().bpm_events_size() == 0);
    REQUIRE(response.begin_edit_response().beat_change_events_size() == 0);
    REQUIRE(response.begin_edit_response().timeline_speed_events_size() == 0);
    REQUIRE(response.begin_edit_response().note_speed_events_size() == 0);
    REQUIRE(response.begin_edit_response().event_scan_extra_tick() == 19200);
    REQUIRE(response.begin_edit_response().event_scan_til_size() == 16);
}

TEST_CASE("router applies append patch")
{
    FakeContext context;
    RequestRouter router(&context);
    margrete::rpc::v1::Envelope request;
    request.set_request_id(21);
    auto *patch = request.mutable_apply_append_patch_request();
    patch->set_name("append");
    patch->add_notes()->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 21);
    REQUIRE(response.has_apply_append_patch_response());
    REQUIRE(context.chart.appendedNotes == 1);
    REQUIRE(context.undo.commitCount == 1);
}

TEST_CASE("router applies edit delta patch without scan")
{
    FakeContext context;
    context.chart.addExistingNote(10)->info.tick = 123;
    context.chart.addExistingBpmEvent(200, 180.0);
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(22);
    auto *delta = request.mutable_apply_edit_delta_request();
    delta->set_name("edit_delta");
    delta->set_replace_all_notes(true);
    delta->add_notes_upsert()->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    delta->add_bpm_ticks_delete(200);
    delta->add_bpm_upsert()->set_tick(240);

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 22);
    REQUIRE(response.has_apply_edit_delta_response());
    REQUIRE(context.chart.deletedNotes >= 1);
    REQUIRE(context.chart.appendedNotes >= 1);
    REQUIRE(context.chart.deletedEvents >= 1);
    REQUIRE(context.undo.commitCount == 1);
}
