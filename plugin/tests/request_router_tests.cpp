#include <catch2/catch_test_macros.hpp>

#include "Config.h"
#include "FakeMargrete.h"
#include "RequestRouter.h"
#include "margrete/rpc/v1/messages.pb.h"
#include "meta.h"

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
}

TEST_CASE("router responds to status")
{
    FakeContext context;
    RequestRouter router(&context);
    router.setInstanceId("test-instance");
    router.setStatusSnapshotProvider([]() {
        RouterStatusSnapshot snapshot;
        snapshot.uptime = 42;
        snapshot.pid = 1234;
        snapshot.logPath = "C:\\logs\\margrete-rpc.log";
        snapshot.configPath = "C:\\config\\margrete-rpc.ini";
        return snapshot;
    });
    margrete::rpc::v1::Envelope request;
    request.set_request_id(12);
    request.mutable_status_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 12);
    REQUIRE(response.has_status_response());
    REQUIRE(response.status_response().server_name() == "Margrete RPC");
    REQUIRE(response.status_response().server_version() == PRODUCT_VERSION);
    REQUIRE(response.status_response().server_build_time() == BUILD_TIME);
    REQUIRE_FALSE(response.status_response().server_build_time().empty());
    REQUIRE(response.status_response().instance_id() == "test-instance");
    REQUIRE(response.status_response().uptime() == 42);
    REQUIRE(response.status_response().pid() == 1234);
    REQUIRE(response.status_response().log_path() == "C:\\logs\\margrete-rpc.log");
    REQUIRE(response.status_response().config_path() == "C:\\config\\margrete-rpc.ini");
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

TEST_CASE("router applies edit request")
{
    FakeContext context;
    context.chart.addExistingNote(10)->info.tick = 123;
    context.chart.addExistingBpmEvent(200, 180.0);
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(22);
    auto *edit = request.mutable_apply_edit_request();
    edit->set_name("edit");
    edit->set_replace_all_notes(true);
    edit->add_notes_upsert()->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    edit->add_bpm_ticks_delete(200);
    edit->add_bpm_upsert()->set_tick(240);

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 22);
    REQUIRE(response.has_apply_edit_response());
    REQUIRE(context.chart.deletedNotes >= 1);
    REQUIRE(context.chart.appendedNotes >= 1);
    REQUIRE(context.chart.deletedEvents >= 1);
    REQUIRE(context.undo.commitCount == 1);
}

TEST_CASE("router invokes undo and reports result")
{
    FakeContext context;
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(24);
    request.mutable_undo_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 24);
    REQUIRE(response.has_undo_response());
    REQUIRE(response.undo_response().success() == true);
    REQUIRE(context.undo.undoCount == 1);
}

TEST_CASE("router invokes redo and reports result")
{
    FakeContext context;
    context.undo.canRedoResult = MP_TRUE;
    context.undo.redoResult = MP_FALSE;
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(25);
    request.mutable_redo_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 25);
    REQUIRE(response.has_redo_response());
    REQUIRE(response.redo_response().success() == false);
    REQUIRE(context.undo.redoCount == 1);
}

TEST_CASE("router skips undo when undo is unavailable")
{
    FakeContext context;
    context.undo.canUndoResult = MP_FALSE;
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(28);
    request.mutable_undo_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 28);
    REQUIRE(response.has_undo_response());
    REQUIRE(response.undo_response().success() == false);
    REQUIRE(context.undo.undoCount == 0);
}

TEST_CASE("router skips redo when redo is unavailable")
{
    FakeContext context;
    context.undo.canRedoResult = MP_FALSE;
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(29);
    request.mutable_redo_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 29);
    REQUIRE(response.has_redo_response());
    REQUIRE(response.redo_response().success() == false);
    REQUIRE(context.undo.redoCount == 0);
}

TEST_CASE("router returns current tick")
{
    FakeContext context;
    context.currentTick = 1234;
    RequestRouter router(&context);

    margrete::rpc::v1::Envelope request;
    request.set_request_id(26);
    request.mutable_current_tick_request();

    const auto response = router.route(request);

    REQUIRE(response.request_id() == 26);
    REQUIRE(response.has_current_tick_response());
    REQUIRE(response.current_tick_response().current_tick() == 1234);
}
