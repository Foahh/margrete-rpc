#include "TransactionApplier.h"

#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "ChartMapper.h"

namespace
{
void Check(MpBoolean ok, const char *message)
{
    if (ok != MP_TRUE)
    {
        throw std::runtime_error(message);
    }
}

IMargretePluginNote *CreateNoteTree(IMargretePluginChart &chart, const margrete::rpc::v1::Note &proto)
{
    IMargretePluginNote *note = nullptr;
    Check(chart.createNote(&note), "failed to create note");
    const MP_NOTEINFO info = ChartMapper::ProtoToNoteInfo(proto);
    note->setInfo(&info);
    for (const auto &childProto : proto.children())
    {
        IMargretePluginNote *child = CreateNoteTree(chart, childProto);
        Check(note->appendChild(child), "failed to append child note");
    }
    return note;
}

void UpsertNoteTree(IMargretePluginNote &existing, const margrete::rpc::v1::Note &proto)
{
    const MP_NOTEINFO info = ChartMapper::ProtoToNoteInfo(proto);
    existing.setInfo(&info);

    std::unordered_map<int, IMargretePluginNote *> childById;
    const MpInteger childCount = existing.getChildrenCount();
    std::vector<MargreteComPtr<IMargretePluginNote>> children;
    children.reserve(static_cast<std::size_t>(childCount));
    for (MpInteger index = 0; index < childCount; ++index)
    {
        IMargretePluginNote *child = nullptr;
        Check(existing.getChild(index, &child), "failed to read child note");
        if (!child)
        {
            throw std::runtime_error("child note is unavailable");
        }
        children.emplace_back(child);
        childById.emplace(children.back()->getId(), children.back().get());
    }

    for (const auto &childProto : proto.children())
    {
        if (!childProto.has_id())
        {
            throw std::invalid_argument("in-place note upsert requires child ids");
        }
        auto found = childById.find(childProto.id());
        if (found == childById.end())
        {
            throw std::invalid_argument("note upsert references unknown child id");
        }
        UpsertNoteTree(*found->second, childProto);
    }
}

void ApplyBpmEvent(IMargretePluginChart &chart, const margrete::rpc::v1::BpmEvent &proto)
{
    void *existing = nullptr;
    MP_EVENT_BPMINFO info{};
    info.tick = proto.tick();
    info.bpm = proto.bpm();
    if (chart.findEventBpm(proto.tick(), &existing) == MP_TRUE && existing)
    {
        auto *event = static_cast<IMargretePluginEventBpm *>(existing);
        event->setInfo(&info);
        return;
    }
    void *created = nullptr;
    Check(chart.createEvent(IID_IMargretePluginEventBpm, &created), "failed to create bpm event");
    auto *event = static_cast<IMargretePluginEventBpm *>(created);
    event->setInfo(&info);
    Check(chart.appendEvent(event), "failed to append bpm event");
}

void ApplyBeatChangeEvent(IMargretePluginChart &chart, const margrete::rpc::v1::BeatChangeEvent &proto)
{
    void *existing = nullptr;
    MP_EVENT_BCINFO info{};
    info.bar = proto.bar();
    info.beatsPerBar = proto.beats_per_bar();
    info.beatUnit = proto.beat_unit();
    if (chart.findEventBeatChange(proto.bar(), &existing) == MP_TRUE && existing)
    {
        static_cast<IMargretePluginEventBeatChange *>(existing)->setInfo(&info);
        return;
    }
    void *created = nullptr;
    Check(chart.createEvent(IID_IMargretePluginEventBeatChange, &created), "failed to create beat event");
    auto *event = static_cast<IMargretePluginEventBeatChange *>(created);
    event->setInfo(&info);
    Check(chart.appendEvent(event), "failed to append beat event");
}

void ApplyTimelineSpeedEvent(IMargretePluginChart &chart, const margrete::rpc::v1::TimelineSpeedEvent &proto)
{
    void *existing = nullptr;
    MP_EVENT_TLSINFO info{};
    info.tick = proto.tick();
    info.timelineId = proto.timeline_id();
    info.speed = proto.speed();
    if (chart.findEventTimelineSpeed(proto.tick(), proto.timeline_id(), &existing) == MP_TRUE && existing)
    {
        static_cast<IMargretePluginEventTimelineSpeed *>(existing)->setInfo(&info);
        return;
    }
    void *created = nullptr;
    Check(chart.createEvent(IID_IMargretePluginEventTimelineSpeed, &created), "failed to create timeline speed event");
    auto *event = static_cast<IMargretePluginEventTimelineSpeed *>(created);
    event->setInfo(&info);
    Check(chart.appendEvent(event), "failed to append timeline speed event");
}

void ApplyNoteSpeedEvent(IMargretePluginChart &chart, const margrete::rpc::v1::NoteSpeedEvent &proto)
{
    void *existing = nullptr;
    MP_EVENT_NSMINFO info{};
    info.tick = proto.tick();
    info.speed = proto.speed();
    if (chart.findEventNoteSpeedModifier(proto.tick(), &existing) == MP_TRUE && existing)
    {
        static_cast<IMargretePluginEventNoteSpeedModifier *>(existing)->setInfo(&info);
        return;
    }
    void *created = nullptr;
    Check(chart.createEvent(IID_IMargretePluginEventNoteSpeedModifier, &created), "failed to create note speed event");
    auto *event = static_cast<IMargretePluginEventNoteSpeedModifier *>(created);
    event->setInfo(&info);
    Check(chart.appendEvent(event), "failed to append note speed event");
}

std::vector<MargreteComPtr<IMargretePluginNote>> CurrentRootNotes(IMargretePluginChart &chart)
{
    std::vector<MargreteComPtr<IMargretePluginNote>> notes;
    const MpInteger count = chart.getNotesCount();
    notes.reserve(static_cast<std::size_t>(count));
    for (MpInteger index = 0; index < count; ++index)
    {
        IMargretePluginNote *note = nullptr;
        Check(chart.getNote(index, &note), "failed to read existing note");
        if (!note)
        {
            throw std::runtime_error("root note is unavailable");
        }
        notes.emplace_back(note);
    }
    return notes;
}

template <typename Fn> void WithUndo(MargreteSession &session, Fn fn)
{
    Check(session.undoBuffer().beginRecording(), "failed to begin undo recording");
    try
    {
        fn();
        Check(session.undoBuffer().commitRecording(), "failed to commit undo recording");
        session.update();
    }
    catch (...)
    {
        session.undoBuffer().discardRecording();
        throw;
    }
}

void DeleteAllRootNotes(IMargretePluginChart &chart)
{
    const MpInteger count = chart.getNotesCount();
    for (MpInteger index = count; index > 0; --index)
    {
        IMargretePluginNote *note = nullptr;
        Check(chart.getNote(index - 1, &note), "failed to read existing note");
        if (!note)
        {
            throw std::runtime_error("root note is unavailable");
        }
        MargreteComPtr<IMargretePluginNote> owned(note);
        Check(chart.deleteNote(owned.get()), "failed to delete note");
    }
}

void ApplyEditNotes(IMargretePluginChart &chart, const margrete::rpc::v1::ApplyEditRequest &request)
{
    if (request.replace_all_notes())
    {
        DeleteAllRootNotes(chart);
        for (const auto &noteProto : request.notes_upsert())
        {
            if (noteProto.has_id())
            {
                throw std::invalid_argument("replace_all_notes cannot contain existing note ids");
            }
            IMargretePluginNote *note = CreateNoteTree(chart, noteProto);
            Check(chart.appendNote(note), "failed to append desired root note");
        }
        return;
    }

    if (request.note_ids_delete_size() > 0)
    {
        std::unordered_set<int> deleteIds;
        deleteIds.reserve(static_cast<std::size_t>(request.note_ids_delete_size()));
        for (const int id : request.note_ids_delete())
        {
            deleteIds.insert(id);
        }
        std::vector<MargreteComPtr<IMargretePluginNote>> roots;
        const MpInteger count = chart.getNotesCount();
        roots.reserve(static_cast<std::size_t>(count));
        for (MpInteger index = 0; index < count; ++index)
        {
            IMargretePluginNote *note = nullptr;
            Check(chart.getNote(index, &note), "failed to read existing note");
            if (!note)
            {
                throw std::runtime_error("root note is unavailable");
            }
            roots.emplace_back(note);
        }
        for (auto &note : roots)
        {
            if (deleteIds.contains(note->getId()))
            {
                Check(chart.deleteNote(note.get()), "failed to delete note");
            }
        }
    }

    if (request.notes_upsert_size() > 0)
    {
        std::unordered_map<int, IMargretePluginNote *> existingById;
        auto roots = CurrentRootNotes(chart);
        for (auto &note : roots)
        {
            existingById.emplace(note->getId(), note.get());
        }

        for (const auto &proto : request.notes_upsert())
        {
            if (proto.has_id())
            {
                auto found = existingById.find(proto.id());
                if (found == existingById.end())
                {
                    throw std::invalid_argument("note upsert references unknown note id");
                }
                UpsertNoteTree(*found->second, proto);
            }
            else
            {
                IMargretePluginNote *note = CreateNoteTree(chart, proto);
                Check(chart.appendNote(note), "failed to append desired root note");
            }
        }
    }
}

void ApplyEditEvents(IMargretePluginChart &chart, const margrete::rpc::v1::ApplyEditRequest &request)
{
    for (const int tick : request.bpm_ticks_delete())
    {
        void *existing = nullptr;
        if (chart.findEventBpm(tick, &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(
                      static_cast<IMargretePluginEvent *>(static_cast<IMargretePluginEventBpm *>(existing))),
                  "failed to delete bpm event");
        }
    }
    for (const int bar : request.beat_bars_delete())
    {
        void *existing = nullptr;
        if (chart.findEventBeatChange(bar, &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(
                      static_cast<IMargretePluginEvent *>(static_cast<IMargretePluginEventBeatChange *>(existing))),
                  "failed to delete beat change event");
        }
    }
    for (const auto &key : request.til_keys_delete())
    {
        void *existing = nullptr;
        if (chart.findEventTimelineSpeed(key.tick(), key.timeline_id(), &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(
                      static_cast<IMargretePluginEvent *>(static_cast<IMargretePluginEventTimelineSpeed *>(existing))),
                  "failed to delete timeline speed event");
        }
    }
    for (const int tick : request.note_speed_ticks_delete())
    {
        void *existing = nullptr;
        if (chart.findEventNoteSpeedModifier(tick, &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(static_cast<IMargretePluginEvent *>(
                      static_cast<IMargretePluginEventNoteSpeedModifier *>(existing))),
                  "failed to delete note speed event");
        }
    }

    for (const auto &eventProto : request.bpm_upsert())
    {
        ApplyBpmEvent(chart, eventProto);
    }
    for (const auto &eventProto : request.beat_upsert())
    {
        ApplyBeatChangeEvent(chart, eventProto);
    }
    for (const auto &eventProto : request.til_upsert())
    {
        ApplyTimelineSpeedEvent(chart, eventProto);
    }
    for (const auto &eventProto : request.note_speed_upsert())
    {
        ApplyNoteSpeedEvent(chart, eventProto);
    }
}
} // namespace

void TransactionApplier::ApplyEdit(MargreteSession &session, const margrete::rpc::v1::ApplyEditRequest &request)
{
    WithUndo(session, [&]() {
        ApplyEditNotes(session.chart(), request);
        ApplyEditEvents(session.chart(), request);
    });
}
