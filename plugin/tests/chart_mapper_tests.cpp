#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#include "ChartMapper.h"
#include "FakeMargrete.h"

using Catch::Matchers::ContainsSubstring;

TEST_CASE("raw note node appends root note with child")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *raw = item.mutable_raw_note();
    raw->set_type(margrete::rpc::v1::NOTE_TYPE_SLIDE);
    raw->set_long_attr(margrete::rpc::v1::LONG_ATTR_BEGIN);
    raw->set_x(4);
    raw->set_width(2);
    raw->set_tick(100);
    auto *child = raw->add_children();
    child->set_type(margrete::rpc::v1::NOTE_TYPE_SLIDE);
    child->set_long_attr(margrete::rpc::v1::LONG_ATTR_END);
    child->set_x(6);
    child->set_width(2);
    child->set_tick(580);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedNotes == 1);
    REQUIRE(chart.createdNotes.size() == 2);
    REQUIRE(chart.createdNotes[0]->children.size() == 1);
}

TEST_CASE("hold appends begin note with end child")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *hold = item.mutable_note()->mutable_hold();
    hold->mutable_base()->set_tick(200);
    hold->mutable_base()->set_lane(3);
    hold->mutable_base()->set_width(4);
    hold->set_duration(960);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedNotes == 1);
    REQUIRE(chart.createdNotes.size() == 2);
    REQUIRE(chart.createdNotes[0]->info.type == MP_NOTETYPE_HOLD);
    REQUIRE(chart.createdNotes[0]->children.size() == 1);
}

TEST_CASE("air hold appends begin note with end child and height")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *airHold = item.mutable_note()->mutable_air_hold();
    airHold->mutable_base()->set_tick(300);
    airHold->mutable_base()->set_lane(1);
    airHold->mutable_base()->set_width(2);
    airHold->mutable_base()->set_timeline(0);
    airHold->set_duration(480);
    airHold->set_height(64);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedNotes == 1);
    REQUIRE(chart.createdNotes.size() == 2);
    REQUIRE(chart.createdNotes[0]->info.type == MP_NOTETYPE_AIRHOLD);
    REQUIRE(chart.createdNotes[0]->info.height == 64);
    REQUIRE(chart.createdNotes[0]->children.size() == 1);
    IMargretePluginNote *endNote = chart.createdNotes[0]->children[0];
    REQUIRE(endNote != nullptr);
    MP_NOTEINFO endInfo{};
    endNote->getInfo(&endInfo);
    REQUIRE(endInfo.type == MP_NOTETYPE_AIRHOLD);
    REQUIRE(endInfo.longAttr == MP_NOTELONGATTR_END);
    REQUIRE(endInfo.height == 64);
}

TEST_CASE("empty append item throws")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;

    REQUIRE_THROWS_WITH(mapper.appendItem(chart, item), ContainsSubstring("append item is empty"));
}

TEST_CASE("tap appends single lane note")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *tap = item.mutable_note()->mutable_tap();
    tap->mutable_base()->set_tick(10);
    tap->mutable_base()->set_lane(2);
    tap->mutable_base()->set_width(3);
    tap->mutable_base()->set_timeline(0);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedNotes == 1);
    REQUIRE(chart.createdNotes.size() == 1);
    REQUIRE(chart.createdNotes[0]->info.type == MP_NOTETYPE_TAP);
}

TEST_CASE("slide with two points appends root and one child")
{
    FakeChart chart;
    ChartMapper mapper;
    margrete::rpc::v1::AppendItem item;
    auto *slide = item.mutable_note()->mutable_slide();
    slide->mutable_base()->set_tick(0);
    slide->mutable_base()->set_lane(1);
    slide->mutable_base()->set_width(2);
    slide->mutable_base()->set_timeline(0);
    slide->add_points();
    auto *end = slide->add_points();
    end->set_dt(120);
    end->set_lane(3);
    end->set_width(2);
    end->set_attr(margrete::rpc::v1::LONG_ATTR_END);

    mapper.appendItem(chart, item);

    REQUIRE(chart.appendedNotes == 1);
    REQUIRE(chart.createdNotes.size() == 2);
    REQUIRE(chart.createdNotes[0]->info.type == MP_NOTETYPE_SLIDE);
    REQUIRE(chart.createdNotes[0]->children.size() == 1);
}
