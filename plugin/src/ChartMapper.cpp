#include "ChartMapper.h"

#include <stdexcept>

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
        notes.push_back(NoteToProto(*note));
    }
    return notes;
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
