#include "ChartMapper.h"

#include <stdexcept>

void ChartMapper::appendItem(IMargretePluginChart& chart, const margrete::rpc::v1::AppendItem& item) const {
    if (item.has_note() && item.note().has_tap()) {
        appendTap(chart, item.note().tap());
        return;
    }
    throw std::runtime_error("append item type is not implemented");
}

void ChartMapper::appendTap(IMargretePluginChart& chart, const margrete::rpc::v1::Tap& tap) const {
    IMargretePluginNote* note = nullptr;
    if (chart.createNote(&note) != MP_TRUE || !note) {
        throw std::runtime_error("failed to create note");
    }
    const auto& base = tap.base();
    MP_NOTEINFO info{};
    info.type = MP_NOTETYPE_TAP;
    info.longAttr = MP_NOTELONGATTR_NONE;
    info.direction = MP_NOTEDIR_NONE;
    info.exAttr = MP_NOTEEXATTR_NONE;
    info.x = base.lane();
    info.width = base.width();
    info.tick = base.tick();
    info.timelineId = base.timeline();
    note->setInfo(&info);
    if (chart.appendNote(note) != MP_TRUE) {
        throw std::runtime_error("failed to append note");
    }
}
