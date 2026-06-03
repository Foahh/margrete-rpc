#include "ChartMapper.h"

#include <algorithm>
#include <stdexcept>
#include <unordered_set>

namespace
{
margrete::rpc::v1::NoteType ToProtoNoteType(MpInteger value)
{
    return static_cast<margrete::rpc::v1::NoteType>(value);
}

margrete::rpc::v1::LongAttr ToProtoLongAttr(MpInteger value)
{
    return static_cast<margrete::rpc::v1::LongAttr>(value);
}

margrete::rpc::v1::Direction ToProtoDirection(MpInteger value)
{
    return static_cast<margrete::rpc::v1::Direction>(value);
}

margrete::rpc::v1::ExAttr ToProtoExAttr(MpInteger value)
{
    return static_cast<margrete::rpc::v1::ExAttr>(value);
}

MpInteger LastNoteTick(const margrete::rpc::v1::Note &note)
{
    MpInteger tick = note.tick();
    for (const auto &child : note.children())
    {
        tick = std::max(tick, LastNoteTick(child));
    }
    return tick;
}

void AddBpmEvent(IMargretePluginEventBpm &event, margrete::rpc::v1::BeginEditResponse &response)
{
    MP_EVENT_BPMINFO info{};
    event.getInfo(&info);
    auto *proto = response.add_bpm_events();
    proto->set_tick(info.tick);
    proto->set_bpm(info.bpm);
}

void AddBeatEvent(IMargretePluginEventBeatChange &event, margrete::rpc::v1::BeginEditResponse &response)
{
    MP_EVENT_BCINFO info{};
    event.getInfo(&info);
    auto *proto = response.add_beat_change_events();
    proto->set_bar(info.bar);
    proto->set_beats_per_bar(info.beatsPerBar);
    proto->set_beat_unit(info.beatUnit);
}

void AddTimelineSpeedEvent(IMargretePluginEventTimelineSpeed &event, margrete::rpc::v1::BeginEditResponse &response)
{
    MP_EVENT_TLSINFO info{};
    event.getInfo(&info);
    auto *proto = response.add_timeline_speed_events();
    proto->set_tick(info.tick);
    proto->set_timeline_id(info.timelineId);
    proto->set_speed(info.speed);
}

void AddNoteSpeedEvent(IMargretePluginEventNoteSpeedModifier &event, margrete::rpc::v1::BeginEditResponse &response)
{
    MP_EVENT_NSMINFO info{};
    event.getInfo(&info);
    auto *proto = response.add_note_speed_events();
    proto->set_tick(info.tick);
    proto->set_speed(info.speed);
}

void CollectTimelineIdsFromNote(const margrete::rpc::v1::Note &note, std::unordered_set<std::int32_t> &out)
{
    out.insert(note.timeline_id());
    for (const auto &child : note.children())
    {
        CollectTimelineIdsFromNote(child, out);
    }
}

std::vector<std::int32_t> FilterEventScanTilByNotes(const std::vector<margrete::rpc::v1::Note> &notes,
                                                    const std::vector<std::int32_t> &eventScanTil)
{
    std::unordered_set<std::int32_t> used;
    for (const auto &n : notes)
    {
        CollectTimelineIdsFromNote(n, used);
    }
    std::vector<std::int32_t> filtered;
    filtered.reserve(eventScanTil.size());
    for (const std::int32_t til : eventScanTil)
    {
        if (used.count(til) != 0)
        {
            filtered.push_back(til);
        }
    }
    return filtered;
}
} // namespace

std::vector<margrete::rpc::v1::Note> ChartMapper::SnapshotNotes(IMargretePluginChart &chart)
{
    std::vector<margrete::rpc::v1::Note> notes;
    const MpInteger count = chart.getNotesCount();
    notes.reserve(static_cast<std::size_t>(count));
    for (MpInteger index = 0; index < count; ++index)
    {
        IMargretePluginNote *note = nullptr;
        if (chart.getNote(index, &note) != MP_TRUE || !note)
        {
            throw std::runtime_error("failed to read note from chart");
        }
        MargreteComPtr<IMargretePluginNote> owned(note);
        notes.push_back(NoteToProto(*note));
    }
    return notes;
}

void ChartMapper::SnapshotForEdit(IMargretePluginChart &chart, MpInteger eventScanExtraTicks,
                                  const std::vector<std::int32_t> &eventScanTil, bool eventScanNoteTilOnly,
                                  margrete::rpc::v1::BeginEditResponse &response)
{
    response.set_scan(true);

    const auto notes = SnapshotNotes(chart);

    MpInteger lastNoteTick = 0;
    for (const auto &note : notes)
    {
        lastNoteTick = std::max(lastNoteTick, LastNoteTick(note));
        *response.add_notes() = note;
    }

    std::vector<std::int32_t> scanTil = eventScanTil;
    if (eventScanNoteTilOnly)
    {
        scanTil = FilterEventScanTilByNotes(notes, eventScanTil);
    }

    const MpInteger scanUntil = lastNoteTick + eventScanExtraTicks;
    response.set_event_scan_extra_tick(eventScanExtraTicks);
    response.mutable_event_scan_til()->Assign(scanTil.begin(), scanTil.end());

    for (MpInteger tick = 0; tick <= scanUntil; ++tick)
    {
        void *found = nullptr;
        if (chart.findEventBpm(tick, &found) == MP_TRUE && found)
        {
            MargreteComPtr<IMargretePluginEventBpm> event(static_cast<IMargretePluginEventBpm *>(found));
            AddBpmEvent(*event, response);
        }

        found = nullptr;
        if (chart.findEventNoteSpeedModifier(tick, &found) == MP_TRUE && found)
        {
            MargreteComPtr<IMargretePluginEventNoteSpeedModifier> event(
                static_cast<IMargretePluginEventNoteSpeedModifier *>(found));
            AddNoteSpeedEvent(*event, response);
        }

        found = nullptr;
        if (chart.findEventBeatChange(tick, &found) == MP_TRUE && found)
        {
            MargreteComPtr<IMargretePluginEventBeatChange> event(static_cast<IMargretePluginEventBeatChange *>(found));
            AddBeatEvent(*event, response);
        }

        for (const std::int32_t timelineId : scanTil)
        {
            found = nullptr;
            if (chart.findEventTimelineSpeed(tick, timelineId, &found) == MP_TRUE && found)
            {
                MargreteComPtr<IMargretePluginEventTimelineSpeed> event(
                    static_cast<IMargretePluginEventTimelineSpeed *>(found));
                AddTimelineSpeedEvent(*event, response);
            }
        }
    }
}

margrete::rpc::v1::Note ChartMapper::NoteToProto(IMargretePluginNote &note)
{
    MP_NOTEINFO info{};
    note.getInfo(&info);

    margrete::rpc::v1::Note proto;
    proto.set_id(note.getId());
    proto.set_type(ToProtoNoteType(info.type));
    proto.set_long_attr(ToProtoLongAttr(info.longAttr));
    proto.set_direction(ToProtoDirection(info.direction));
    proto.set_ex_attr(ToProtoExAttr(info.exAttr));
    proto.set_variation_id(info.variationId);
    proto.set_x(info.x);
    proto.set_width(info.width);
    proto.set_height(info.height);
    proto.set_tick(info.tick);
    proto.set_timeline_id(info.timelineId);
    proto.set_option_value(info.optionValue);

    const MpInteger childCount = note.getChildrenCount();
    for (MpInteger index = 0; index < childCount; ++index)
    {
        IMargretePluginNote *child = nullptr;
        if (note.getChild(index, &child) != MP_TRUE || !child)
        {
            throw std::runtime_error("failed to read child note");
        }
        MargreteComPtr<IMargretePluginNote> owned(child);
        *proto.add_children() = NoteToProto(*child);
    }
    return proto;
}

MP_NOTEINFO ChartMapper::ProtoToNoteInfo(const margrete::rpc::v1::Note &note)
{
    MP_NOTEINFO info{};
    info.type = note.type();
    info.longAttr = note.long_attr();
    info.direction = note.direction();
    info.exAttr = note.ex_attr();
    info.variationId = note.variation_id();
    info.x = note.x();
    info.width = note.width();
    info.height = note.height();
    info.tick = note.tick();
    info.timelineId = note.timeline_id();
    info.optionValue = note.option_value();
    return info;
}
