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
