#include "TransactionApplier.h"

#include <stdexcept>
#include <set>
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

template <typename Request> void ApplyEvents(IMargretePluginChart &chart, const Request &request)
{
    for (const auto &eventProto : request.bpm_events())
    {
        ApplyBpmEvent(chart, eventProto);
    }
    for (const auto &eventProto : request.beat_change_events())
    {
        ApplyBeatChangeEvent(chart, eventProto);
    }
    for (const auto &eventProto : request.timeline_speed_events())
    {
        ApplyTimelineSpeedEvent(chart, eventProto);
    }
    for (const auto &eventProto : request.note_speed_events())
    {
        ApplyNoteSpeedEvent(chart, eventProto);
    }
}

void DeleteMissingBpmEvents(IMargretePluginChart &chart, const margrete::rpc::v1::ApplyEditPatchRequest &request)
{
    std::unordered_set<int> finalTicks;
    for (const auto &eventProto : request.bpm_events())
    {
        finalTicks.insert(eventProto.tick());
    }
    for (MpInteger tick = 0; tick <= request.event_scan_until_tick(); ++tick)
    {
        void *existing = nullptr;
        if (!finalTicks.contains(tick) && chart.findEventBpm(tick, &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(static_cast<IMargretePluginEvent *>(static_cast<IMargretePluginEventBpm *>(existing))),
                  "failed to delete bpm event");
        }
    }
}

void DeleteMissingBeatChangeEvents(IMargretePluginChart &chart,
                                   const margrete::rpc::v1::ApplyEditPatchRequest &request)
{
    std::unordered_set<int> finalBars;
    for (const auto &eventProto : request.beat_change_events())
    {
        finalBars.insert(eventProto.bar());
    }
    for (MpInteger bar = 0; bar <= request.event_scan_until_tick(); ++bar)
    {
        void *existing = nullptr;
        if (!finalBars.contains(bar) && chart.findEventBeatChange(bar, &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(
                      static_cast<IMargretePluginEvent *>(static_cast<IMargretePluginEventBeatChange *>(existing))),
                  "failed to delete beat change event");
        }
    }
}

void DeleteMissingTimelineSpeedEvents(IMargretePluginChart &chart,
                                      const margrete::rpc::v1::ApplyEditPatchRequest &request)
{
    std::set<std::pair<int, int>> finalKeys;
    for (const auto &eventProto : request.timeline_speed_events())
    {
        finalKeys.emplace(eventProto.tick(), eventProto.timeline_id());
    }
    for (MpInteger tick = 0; tick <= request.event_scan_until_tick(); ++tick)
    {
        for (const MpInteger timelineId : request.event_scan_timeline_ids())
        {
            void *existing = nullptr;
            if (!finalKeys.contains({tick, timelineId}) &&
                chart.findEventTimelineSpeed(tick, timelineId, &existing) == MP_TRUE && existing)
            {
                Check(chart.deleteEvent(static_cast<IMargretePluginEvent *>(
                          static_cast<IMargretePluginEventTimelineSpeed *>(existing))),
                      "failed to delete timeline speed event");
            }
        }
    }
}

void DeleteMissingNoteSpeedEvents(IMargretePluginChart &chart, const margrete::rpc::v1::ApplyEditPatchRequest &request)
{
    std::unordered_set<int> finalTicks;
    for (const auto &eventProto : request.note_speed_events())
    {
        finalTicks.insert(eventProto.tick());
    }
    for (MpInteger tick = 0; tick <= request.event_scan_until_tick(); ++tick)
    {
        void *existing = nullptr;
        if (!finalTicks.contains(tick) && chart.findEventNoteSpeedModifier(tick, &existing) == MP_TRUE && existing)
        {
            Check(chart.deleteEvent(static_cast<IMargretePluginEvent *>(
                      static_cast<IMargretePluginEventNoteSpeedModifier *>(existing))),
                  "failed to delete note speed event");
        }
    }
}

void ReconcileEvents(IMargretePluginChart &chart, const margrete::rpc::v1::ApplyEditPatchRequest &request)
{
    if (request.event_scan_until_tick() <= 0)
    {
        ApplyEvents(chart, request);
        return;
    }
    DeleteMissingBpmEvents(chart, request);
    DeleteMissingBeatChangeEvents(chart, request);
    DeleteMissingTimelineSpeedEvents(chart, request);
    DeleteMissingNoteSpeedEvents(chart, request);
    ApplyEvents(chart, request);
}

std::vector<IMargretePluginNote *> CurrentRootNotes(IMargretePluginChart &chart)
{
    std::vector<IMargretePluginNote *> notes;
    const MpInteger count = chart.getNotesCount();
    for (MpInteger index = 0; index < count; ++index)
    {
        IMargretePluginNote *note = nullptr;
        Check(chart.getNote(index, &note), "failed to read existing note");
        notes.push_back(note);
    }
    return notes;
}

void ReconcileRootNotes(IMargretePluginChart &chart,
                        const google::protobuf::RepeatedPtrField<margrete::rpc::v1::Note> &finalNotes)
{
    std::unordered_map<int, IMargretePluginNote *> existingById;
    for (auto *note : CurrentRootNotes(chart))
    {
        existingById.emplace(note->getId(), note);
    }

    std::unordered_set<int> keptIds;
    std::vector<IMargretePluginNote *> desiredRoots;
    for (const auto &proto : finalNotes)
    {
        if (proto.has_id())
        {
            auto found = existingById.find(proto.id());
            if (found == existingById.end())
            {
                throw std::invalid_argument("final note tree references unknown note id");
            }
            const MP_NOTEINFO info = ChartMapper::ProtoToNoteInfo(proto);
            found->second->setInfo(&info);
            keptIds.insert(proto.id());
            desiredRoots.push_back(found->second);
        }
        else
        {
            desiredRoots.push_back(CreateNoteTree(chart, proto));
        }
    }

    for (const auto &[id, note] : existingById)
    {
        if (!keptIds.contains(id))
        {
            Check(chart.deleteNote(note), "failed to delete note");
        }
    }

    for (auto *note : desiredRoots)
    {
        Check(chart.appendNote(note), "failed to append desired root note");
    }
}

template <typename Fn> void WithUndo(MargreteSession &session, Fn fn)
{
    Check(session.undo().beginRecording(), "failed to begin undo recording");
    try
    {
        fn();
        Check(session.undo().commitRecording(), "failed to commit undo recording");
        session.update();
    }
    catch (...)
    {
        session.undo().discardRecording();
        throw;
    }
}
} // namespace

void TransactionApplier::ApplyAppend(MargreteSession &session,
                                     const margrete::rpc::v1::ApplyAppendPatchRequest &request)
{
    WithUndo(session, [&]() {
        for (const auto &noteProto : request.notes())
        {
            if (noteProto.has_id())
            {
                throw std::invalid_argument("append patch cannot contain existing note ids");
            }
            IMargretePluginNote *note = CreateNoteTree(session.chart(), noteProto);
            Check(session.chart().appendNote(note), "failed to append note");
        }
        ApplyEvents(session.chart(), request);
    });
}

void TransactionApplier::ApplyEdit(MargreteSession &session, const margrete::rpc::v1::ApplyEditPatchRequest &request)
{
    WithUndo(session, [&]() {
        ReconcileRootNotes(session.chart(), request.notes());
        ReconcileEvents(session.chart(), request);
    });
}
