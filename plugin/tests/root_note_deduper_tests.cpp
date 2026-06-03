#include <catch2/catch_test_macros.hpp>

#include "FakeMargrete.h"
#include "RootNoteDeduper.h"

TEST_CASE("root note deduper removes later duplicate ids")
{
    FakeContext context;
    auto *first = context.chart.addExistingNote(10);
    auto *second = context.chart.addExistingNote(11);
    context.chart.addExistingNote(10);
    context.chart.addExistingNote(11);

    const int removed = RootNoteDeduper::Deduplicate(context.chart);

    REQUIRE(removed == 2);
    REQUIRE(context.chart.deletedNotes == 2);
    REQUIRE(context.chart.notes.size() == 2);
    REQUIRE(context.chart.notes[0] == first);
    REQUIRE(context.chart.notes[1] == second);
}

TEST_CASE("root note deduper leaves unique ids unchanged")
{
    FakeContext context;
    auto *first = context.chart.addExistingNote(10);
    auto *second = context.chart.addExistingNote(11);

    const int removed = RootNoteDeduper::Deduplicate(context.chart);

    REQUIRE(removed == 0);
    REQUIRE(context.chart.deletedNotes == 0);
    REQUIRE(context.chart.notes.size() == 2);
    REQUIRE(context.chart.notes[0] == first);
    REQUIRE(context.chart.notes[1] == second);
}
