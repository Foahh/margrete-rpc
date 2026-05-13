#include <catch2/catch_test_macros.hpp>

#include "ChartMapper.h"
#include "FakeMargrete.h"

TEST_CASE("chart mapper serializes root notes and child notes")
{
    FakeContext context;
    auto *root = context.chart.addExistingNote(10);
    root->info.type = MP_NOTETYPE_SLIDE;
    root->info.longAttr = MP_NOTELONGATTR_BEGIN;
    root->info.direction = MP_NOTEDIR_UPLEFT;
    root->info.exAttr = MP_NOTEEXATTR_HAS_NOTE;
    root->info.variationId = 2;
    root->info.x = 3;
    root->info.width = 2;
    root->info.height = 1;
    root->info.tick = 120;
    root->info.timelineId = 4;
    root->info.optionValue = 9;
    auto *child = context.chart.addDetachedNote(11);
    child->info.type = MP_NOTETYPE_TAP;
    child->info.tick = 180;
    root->children.push_back(child);

    const auto notes = ChartMapper::SnapshotNotes(context.chart);

    REQUIRE(notes.size() == 1);
    REQUIRE(notes[0].id() == 10);
    REQUIRE(notes[0].type() == margrete::rpc::v1::NOTE_TYPE_SLIDE);
    REQUIRE(notes[0].long_attr() == margrete::rpc::v1::LONG_ATTR_BEGIN);
    REQUIRE(notes[0].direction() == margrete::rpc::v1::DIRECTION_UPLEFT);
    REQUIRE(notes[0].ex_attr() == margrete::rpc::v1::EX_ATTR_HAS_NOTE);
    REQUIRE(notes[0].children_size() == 1);
    REQUIRE(notes[0].children(0).id() == 11);
    REQUIRE(notes[0].children(0).tick() == 180);
}

TEST_CASE("chart mapper scans events through configured tick range")
{
    FakeContext context;
    auto *root = context.chart.addExistingNote(10);
    root->info.tick = 1000;
    root->info.timelineId = 2;
    context.chart.addExistingBpmEvent(120, 180.0);
    context.chart.addExistingNoteSpeedEvent(240, 1.25);
    context.chart.addExistingTimelineSpeedEvent(360, 2, 0.75);
    context.chart.addExistingBeatEvent(1, 3, 4);

    margrete::rpc::v1::BeginEditResponse response;
    ChartMapper::SnapshotForEdit(context.chart, 200, 1500, response);

    REQUIRE(response.event_scan_until_tick() == 1200);
    REQUIRE(response.event_scan_max_til() == 1500);
    REQUIRE(response.bpm_events_size() == 1);
    REQUIRE(response.bpm_events(0).tick() == 120);
    REQUIRE(response.bpm_events(0).bpm() == 180.0);
    REQUIRE(response.note_speed_events_size() == 1);
    REQUIRE(response.note_speed_events(0).tick() == 240);
    REQUIRE(response.timeline_speed_events_size() == 1);
    REQUIRE(response.timeline_speed_events(0).timeline_id() == 2);
    REQUIRE(response.beat_change_events_size() == 1);
    REQUIRE(response.beat_change_events(0).bar() == 1);
}
