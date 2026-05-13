#include <catch2/catch_test_macros.hpp>

#include "FakeMargrete.h"
#include "MargreteSession.h"
#include "TransactionApplier.h"

TEST_CASE("apply edit appends notes and child trees inside undo recording")
{
    FakeContext context;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *note = request.add_notes_upsert();
    note->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    note->set_tick(960);
    note->set_x(4);
    note->set_width(1);
    auto *child = note->add_children();
    child->set_type(margrete::rpc::v1::NOTE_TYPE_AIR);
    child->set_tick(970);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.undo.beginCount == 1);
    REQUIRE(context.undo.commitCount == 1);
    REQUIRE(context.undo.discardCount == 0);
    REQUIRE(context.chart.appendedNotes == 1);
    REQUIRE(context.chart.createdNotes.size() == 2);
    REQUIRE(context.updated);
}

TEST_CASE("event operation creates bpm event when key is empty")
{
    FakeContext context;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *event = request.add_bpm_upsert();
    event->set_tick(0);
    event->set_bpm(180.0);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.createdBpmEvents.size() == 1);
    REQUIRE(context.chart.createdBpmEvents[0]->info.tick == 0);
    REQUIRE(context.chart.createdBpmEvents[0]->info.bpm == 180.0);
    REQUIRE(context.chart.appendedEvents == 1);
}

TEST_CASE("event operation replaces bpm event when key overlaps")
{
    FakeContext context;
    auto *existing = context.chart.addExistingBpmEvent(0, 120.0);
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *event = request.add_bpm_upsert();
    event->set_tick(0);
    event->set_bpm(185.0);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(existing->info.bpm == 185.0);
    REQUIRE(context.chart.appendedEvents == 0);
}

TEST_CASE("event operation creates timeline speed by tick and timeline id")
{
    FakeContext context;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *event = request.add_til_upsert();
    event->set_tick(960);
    event->set_timeline_id(2);
    event->set_speed(0.75);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.createdTimelineSpeedEvents.size() == 1);
    REQUIRE(context.chart.createdTimelineSpeedEvents[0]->info.tick == 960);
    REQUIRE(context.chart.createdTimelineSpeedEvents[0]->info.timelineId == 2);
    REQUIRE(context.chart.createdTimelineSpeedEvents[0]->info.speed == 0.75);
}

TEST_CASE("event operation creates beat change and note speed events")
{
    FakeContext context;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *beat = request.add_beat_upsert();
    beat->set_bar(4);
    beat->set_beats_per_bar(3);
    beat->set_beat_unit(8);
    auto *speed = request.add_note_speed_upsert();
    speed->set_tick(1200);
    speed->set_speed(1.25);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.createdBeatEvents.size() == 1);
    REQUIRE(context.chart.createdBeatEvents[0]->info.bar == 4);
    REQUIRE(context.chart.createdBeatEvents[0]->info.beatsPerBar == 3);
    REQUIRE(context.chart.createdBeatEvents[0]->info.beatUnit == 8);
    REQUIRE(context.chart.createdNoteSpeedEvents.size() == 1);
    REQUIRE(context.chart.createdNoteSpeedEvents[0]->info.tick == 1200);
    REQUIRE(context.chart.createdNoteSpeedEvents[0]->info.speed == 1.25);
}

TEST_CASE("apply edit in-place update does not duplicate root notes")
{
    FakeContext context;
    auto *existing = context.chart.addExistingNote(10);
    existing->info.type = MP_NOTETYPE_TAP;
    existing->info.x = 1;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *updated = request.add_notes_upsert();
    updated->set_id(10);
    updated->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    updated->set_x(9);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.notes.size() == 1);
    REQUIRE(context.chart.notes[0]->info.x == 9);
    REQUIRE(context.chart.appendedNotes == 0);
}

TEST_CASE("apply edit updates existing note and creates new note")
{
    FakeContext context;
    auto *existing = context.chart.addExistingNote(10);
    existing->info.type = MP_NOTETYPE_TAP;
    existing->info.x = 1;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *updated = request.add_notes_upsert();
    updated->set_id(10);
    updated->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    updated->set_x(9);
    auto *created = request.add_notes_upsert();
    created->set_type(margrete::rpc::v1::NOTE_TYPE_AIR);
    created->set_tick(1200);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.notes.size() == 2);
    REQUIRE(context.chart.notes[0]->id == 10);
    REQUIRE(context.chart.notes[0]->info.x == 9);
    REQUIRE(context.chart.createdNotes.size() == 1);
    REQUIRE(context.chart.appendedNotes == 1);
}

TEST_CASE("apply edit deletes existing note by id")
{
    FakeContext context;
    context.chart.addExistingNote(10);
    context.chart.addExistingNote(11);
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    request.add_note_ids_delete(10);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.notes.size() == 1);
    REQUIRE(context.chart.notes[0]->id == 11);
    REQUIRE(context.chart.deletedNotes == 1);
}

TEST_CASE("apply edit deletes bpm event by tick")
{
    FakeContext context;
    auto *deleted = context.chart.addExistingBpmEvent(120, 150.0);
    context.chart.addExistingBpmEvent(240, 160.0);
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    request.add_bpm_ticks_delete(120);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.deletedEvents == 1);
    REQUIRE(context.chart.deletedEventPointers.size() == 1);
    REQUIRE(context.chart.deletedEventPointers[0] == deleted);
}
