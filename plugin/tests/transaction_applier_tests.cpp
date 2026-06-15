#include <catch2/catch_test_macros.hpp>

#include "FakeMargrete.h"
#include "MargreteSession.h"
#include "TransactionApplier.h"

TEST_CASE("margrete session releases acquired interfaces")
{
    FakeContext context;

    REQUIRE(context.document.refCountValue() == 1);
    REQUIRE(context.chart.refCountValue() == 1);
    REQUIRE(context.undo.refCountValue() == 1);
    {
        MargreteSession session(context);

        REQUIRE(context.document.refCountValue() == 2);
        REQUIRE(context.chart.refCountValue() == 2);
        REQUIRE(context.undo.refCountValue() == 2);
    }
    REQUIRE(context.document.refCountValue() == 1);
    REQUIRE(context.chart.refCountValue() == 1);
    REQUIRE(context.undo.refCountValue() == 1);
}

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

TEST_CASE("apply edit releases created note when root append fails")
{
    FakeContext context;
    context.chart.appendNoteResult = MP_FALSE;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    request.add_notes_upsert()->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);

    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));

    REQUIRE(context.undo.commitCount == 0);
    REQUIRE(context.undo.discardCount == 1);
    REQUIRE(context.chart.createdNotes.size() == 1);
    REQUIRE(context.chart.createdNotes[0]->refCountValue() == 0);
}

TEST_CASE("apply edit releases created note tree when child append fails")
{
    struct AppendChildResultGuard
    {
        ~AppendChildResultGuard()
        {
            FakeNote::appendChildResult = MP_TRUE;
        }
    } guard;

    FakeNote::appendChildResult = MP_FALSE;
    FakeContext context;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *note = request.add_notes_upsert();
    note->set_type(margrete::rpc::v1::NOTE_TYPE_HOLD);
    note->add_children()->set_type(margrete::rpc::v1::NOTE_TYPE_HOLD);

    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));

    REQUIRE(context.undo.commitCount == 0);
    REQUIRE(context.undo.discardCount == 1);
    REQUIRE(context.chart.createdNotes.size() == 2);
    REQUIRE(context.chart.createdNotes[0]->refCountValue() == 0);
    REQUIRE(context.chart.createdNotes[1]->refCountValue() == 0);
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

TEST_CASE("event operation releases created event when append fails")
{
    FakeContext context;
    context.chart.appendEventResult = MP_FALSE;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *event = request.add_bpm_upsert();
    event->set_tick(0);
    event->set_bpm(180.0);

    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));

    REQUIRE(context.undo.commitCount == 0);
    REQUIRE(context.undo.discardCount == 1);
    REQUIRE(context.chart.createdBpmEvents.size() == 1);
    REQUIRE(context.chart.createdBpmEvents[0]->refCountValue() == 0);
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
    REQUIRE(existing->refCountValue() == 1);
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
    REQUIRE(existing->refCountValue() == 1);
}

TEST_CASE("apply edit updates child notes in place without rebuilding the tree")
{
    FakeContext context;
    auto *root = context.chart.addExistingNote(10);
    root->info.type = MP_NOTETYPE_HOLD;
    root->info.tick = 0;
    auto *child = context.chart.addDetachedNote(11);
    child->info.type = MP_NOTETYPE_HOLD;
    child->info.tick = 480;
    root->children.push_back(child);

    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *updated = request.add_notes_upsert();
    updated->set_id(10);
    updated->set_type(margrete::rpc::v1::NOTE_TYPE_HOLD);
    updated->set_tick(1920);
    auto *updatedChild = updated->add_children();
    updatedChild->set_id(11);
    updatedChild->set_type(margrete::rpc::v1::NOTE_TYPE_HOLD);
    updatedChild->set_tick(2400);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.notes.size() == 1);
    REQUIRE(context.chart.appendedNotes == 0);
    REQUIRE(context.chart.deletedNotes == 0);
    REQUIRE(context.chart.createdNotes.empty());
    REQUIRE(root->info.tick == 1920);
    REQUIRE(child->info.tick == 2400);
    REQUIRE(root->refCountValue() == 1);
    REQUIRE(child->refCountValue() == 1);
}

TEST_CASE("apply edit discards recording when an in-place child id is unknown")
{
    FakeContext context;
    auto *root = context.chart.addExistingNote(10);
    auto *child = context.chart.addDetachedNote(11);
    root->children.push_back(child);

    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *updated = request.add_notes_upsert();
    updated->set_id(10);
    auto *updatedChild = updated->add_children();
    updatedChild->set_id(99);

    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));
    REQUIRE(context.undo.commitCount == 0);
    REQUIRE(context.undo.discardCount == 1);
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

TEST_CASE("apply edit rejects replace_all with note ids")
{
    FakeContext context;
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    request.set_replace_all_notes(true);
    auto *note = request.add_notes_upsert();
    note->set_id(1);
    note->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));
    REQUIRE(context.undo.commitCount == 0);
    REQUIRE(context.undo.discardCount == 1);
}

TEST_CASE("apply edit rejects upsert of unknown note id")
{
    FakeContext context; // chart starts empty
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *note = request.add_notes_upsert();
    note->set_id(99);
    note->set_type(margrete::rpc::v1::NOTE_TYPE_TAP);
    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));
    REQUIRE(context.undo.discardCount == 1);
}

TEST_CASE("apply edit rejects in-place child upsert without child id")
{
    FakeContext context;
    context.chart.addExistingNote(1); // an existing root with id=1
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    auto *note = request.add_notes_upsert();
    note->set_id(1);
    note->set_type(margrete::rpc::v1::NOTE_TYPE_HOLD);
    note->add_children()->set_type(margrete::rpc::v1::NOTE_TYPE_HOLD); // child has no id
    REQUIRE_THROWS(TransactionApplier::ApplyEdit(session, request));
    REQUIRE(context.undo.discardCount == 1);
}

TEST_CASE("apply edit deletes existing note by id")
{
    FakeContext context;
    auto *deleted = context.chart.addExistingNote(10);
    context.chart.addExistingNote(11);
    MargreteSession session(context);
    margrete::rpc::v1::ApplyEditRequest request;
    request.add_note_ids_delete(10);

    TransactionApplier::ApplyEdit(session, request);

    REQUIRE(context.chart.notes.size() == 1);
    REQUIRE(context.chart.notes[0]->id == 11);
    REQUIRE(context.chart.deletedNotes == 1);
    REQUIRE(deleted->refCountValue() == 0);
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
    REQUIRE(deleted->refCountValue() == 0);
}
