#include <catch2/catch_test_macros.hpp>

#include "ChartMapper.h"
#include "FakeMargrete.h"

TEST_CASE("bpm event is created and appended")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *bpm = item.mutable_event()->mutable_bpm();
    bpm->set_tick(240);
    bpm->set_bpm(180.0);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedEvents == 1);
    REQUIRE(chart.createdBpmEvents.size() == 1);
    REQUIRE(chart.createdBpmEvents[0]->info.tick == 240);
    REQUIRE(chart.createdBpmEvents[0]->info.bpm == 180.0);
}

TEST_CASE("beat event is created and appended")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *beat = item.mutable_event()->mutable_beat();
    beat->set_bar(2);
    beat->set_beats_per_bar(3);
    beat->set_beat_unit(4);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedEvents == 1);
    REQUIRE(chart.createdBeatEvents.size() == 1);
    REQUIRE(chart.createdBeatEvents[0]->info.bar == 2);
    REQUIRE(chart.createdBeatEvents[0]->info.beatsPerBar == 3);
    REQUIRE(chart.createdBeatEvents[0]->info.beatUnit == 4);
}

TEST_CASE("scroll speed event is created and appended")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *speed = item.mutable_event()->mutable_scroll_speed();
    speed->set_tick(480);
    speed->set_timeline(1);
    speed->set_speed(1.5);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedEvents == 1);
    REQUIRE(chart.createdTimelineSpeedEvents.size() == 1);
    REQUIRE(chart.createdTimelineSpeedEvents[0]->info.tick == 480);
    REQUIRE(chart.createdTimelineSpeedEvents[0]->info.timelineId == 1);
    REQUIRE(chart.createdTimelineSpeedEvents[0]->info.speed == 1.5);
}

TEST_CASE("note speed event is created and appended")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *speed = item.mutable_event()->mutable_note_speed();
    speed->set_tick(720);
    speed->set_speed(0.75);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedEvents == 1);
    REQUIRE(chart.createdNoteSpeedEvents.size() == 1);
    REQUIRE(chart.createdNoteSpeedEvents[0]->info.tick == 720);
    REQUIRE(chart.createdNoteSpeedEvents[0]->info.speed == 0.75);
}
