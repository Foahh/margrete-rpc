#include "ChartMapper.h"

#include <stdexcept>

namespace {
MP_NOTEINFO BaseInfo(const margrete::rpc::v1::LaneNote& base, MpInteger type) {
    if (base.width() <= 0 || base.tick() < 0 || base.lane() < 0) {
        throw std::runtime_error("invalid note base");
    }
    MP_NOTEINFO info{};
    info.type = type;
    info.longAttr = MP_NOTELONGATTR_NONE;
    info.direction = MP_NOTEDIR_NONE;
    info.exAttr = MP_NOTEEXATTR_NONE;
    info.x = base.lane();
    info.width = base.width();
    info.tick = base.tick();
    info.timelineId = base.timeline();
    return info;
}

MpInteger ToLongAttr(margrete::rpc::v1::LongAttr attr) {
    return static_cast<MpInteger>(attr);
}
} // namespace

void ChartMapper::appendItem(IMargretePluginChart& chart, const margrete::rpc::v1::AppendItem& item) const {
    if (item.has_raw_note()) {
        appendRaw(chart, item.raw_note());
        return;
    }
    if (item.has_event()) {
        appendEvent(chart, item.event());
        return;
    }
    if (!item.has_note()) {
        throw std::runtime_error("append item is empty");
    }

    const auto& note = item.note();
    if (note.has_tap()) {
        appendLaneNote(chart, note.tap().base(), MP_NOTETYPE_TAP, MP_NOTEDIR_NONE);
    } else if (note.has_ex_tap()) {
        appendLaneNote(chart, note.ex_tap().base(), MP_NOTETYPE_EXTAP, static_cast<MpInteger>(note.ex_tap().direction()));
    } else if (note.has_flick()) {
        appendLaneNote(chart, note.flick().base(), MP_NOTETYPE_FLICK, MP_NOTEDIR_NONE);
    } else if (note.has_damage()) {
        appendLaneNote(chart, note.damage().base(), MP_NOTETYPE_DAMAGE, MP_NOTEDIR_NONE);
    } else if (note.has_hold()) {
        appendHold(chart, note.hold());
    } else if (note.has_slide()) {
        appendSlide(chart, note.slide());
    } else if (note.has_air()) {
        appendAir(chart, note.air());
    } else if (note.has_air_hold()) {
        appendAirHold(chart, note.air_hold());
    } else if (note.has_air_slide()) {
        appendAirSlide(chart, note.air_slide());
    } else if (note.has_air_crush()) {
        appendAirCrush(chart, note.air_crush());
    } else {
        throw std::runtime_error("unsupported note object");
    }
}

IMargretePluginNote& ChartMapper::createNote(IMargretePluginChart& chart, const MP_NOTEINFO& info) const {
    IMargretePluginNote* note = nullptr;
    if (chart.createNote(&note) != MP_TRUE || !note) {
        throw std::runtime_error("failed to create note");
    }
    note->setInfo(&info);
    return *note;
}

void ChartMapper::appendLaneNote(IMargretePluginChart& chart, const margrete::rpc::v1::LaneNote& base, MpInteger type, MpInteger direction) const {
    MP_NOTEINFO info = BaseInfo(base, type);
    info.direction = direction;
    IMargretePluginNote& note = createNote(chart, info);
    if (chart.appendNote(&note) != MP_TRUE) {
        throw std::runtime_error("failed to append note");
    }
}

void ChartMapper::appendHold(IMargretePluginChart& chart, const margrete::rpc::v1::Hold& hold) const {
    if (hold.duration() <= 0) {
        throw std::runtime_error("hold duration must be positive");
    }
    MP_NOTEINFO begin = BaseInfo(hold.base(), MP_NOTETYPE_HOLD);
    begin.longAttr = MP_NOTELONGATTR_BEGIN;
    IMargretePluginNote& root = createNote(chart, begin);

    MP_NOTEINFO end = begin;
    end.longAttr = MP_NOTELONGATTR_END;
    end.tick += hold.duration();
    IMargretePluginNote& child = createNote(chart, end);
    root.appendChild(&child);

    if (chart.appendNote(&root) != MP_TRUE) {
        throw std::runtime_error("failed to append hold");
    }
}

void ChartMapper::appendSlide(IMargretePluginChart& chart, const margrete::rpc::v1::Slide& slide) const {
    if (slide.points_size() < 2) {
        throw std::runtime_error("slide requires at least two points");
    }
    MP_NOTEINFO begin = BaseInfo(slide.base(), MP_NOTETYPE_SLIDE);
    begin.longAttr = MP_NOTELONGATTR_BEGIN;
    IMargretePluginNote& root = createNote(chart, begin);
    for (int i = 1; i < slide.points_size(); ++i) {
        const auto& point = slide.points(i);
        MP_NOTEINFO info = begin;
        info.longAttr = i == slide.points_size() - 1 ? MP_NOTELONGATTR_END : ToLongAttr(point.attr());
        info.tick = slide.base().tick() + point.dt();
        info.x = point.lane();
        info.width = point.width();
        IMargretePluginNote& child = createNote(chart, info);
        root.appendChild(&child);
    }
    if (chart.appendNote(&root) != MP_TRUE) {
        throw std::runtime_error("failed to append slide");
    }
}

void ChartMapper::appendAir(IMargretePluginChart& chart, const margrete::rpc::v1::Air& air) const {
    MP_NOTEINFO info = BaseInfo(air.base(), MP_NOTETYPE_AIR);
    info.direction = static_cast<MpInteger>(air.direction());
    info.exAttr = static_cast<MpInteger>(air.ex_attr());
    IMargretePluginNote& note = createNote(chart, info);
    if (chart.appendNote(&note) != MP_TRUE) {
        throw std::runtime_error("failed to append air");
    }
}

void ChartMapper::appendAirHold(IMargretePluginChart& chart, const margrete::rpc::v1::AirHold& airHold) const {
    if (airHold.duration() <= 0) {
        throw std::runtime_error("air hold duration must be positive");
    }
    MP_NOTEINFO begin = BaseInfo(airHold.base(), MP_NOTETYPE_AIRHOLD);
    begin.longAttr = MP_NOTELONGATTR_BEGIN;
    begin.height = airHold.height();
    IMargretePluginNote& root = createNote(chart, begin);

    MP_NOTEINFO end = begin;
    end.longAttr = MP_NOTELONGATTR_END;
    end.tick += airHold.duration();
    end.height = airHold.height();
    IMargretePluginNote& child = createNote(chart, end);
    root.appendChild(&child);

    if (chart.appendNote(&root) != MP_TRUE) {
        throw std::runtime_error("failed to append air hold");
    }
}

void ChartMapper::appendAirSlide(IMargretePluginChart& chart, const margrete::rpc::v1::AirSlide& airSlide) const {
    if (airSlide.points_size() < 2) {
        throw std::runtime_error("air slide requires at least two points");
    }
    const auto& base = airSlide.base();
    MP_NOTEINFO tap = BaseInfo(base, MP_NOTETYPE_TAP);
    IMargretePluginNote& tapNote = createNote(chart, tap);

    MP_NOTEINFO air = tap;
    air.type = MP_NOTETYPE_AIR;
    air.direction = static_cast<MpInteger>(airSlide.air_direction());
    air.exAttr = static_cast<MpInteger>(airSlide.air_ex_attr());
    IMargretePluginNote& airNote = createNote(chart, air);

    MP_NOTEINFO rootInfo = tap;
    rootInfo.type = MP_NOTETYPE_AIRSLIDE;
    rootInfo.longAttr = MP_NOTELONGATTR_BEGIN;
    rootInfo.height = airSlide.points(0).height();
    IMargretePluginNote& root = createNote(chart, rootInfo);
    for (int i = 1; i < airSlide.points_size(); ++i) {
        const auto& point = airSlide.points(i);
        MP_NOTEINFO info = rootInfo;
        info.longAttr = i == airSlide.points_size() - 1 ? MP_NOTELONGATTR_END : ToLongAttr(point.attr());
        info.tick = base.tick() + point.dt();
        info.x = point.lane();
        info.height = point.height();
        IMargretePluginNote& child = createNote(chart, info);
        root.appendChild(&child);
    }

    airNote.appendChild(&root);
    tapNote.appendChild(&airNote);
    if (chart.appendNote(&tapNote) != MP_TRUE) {
        throw std::runtime_error("failed to append air slide");
    }
}

void ChartMapper::appendAirCrush(IMargretePluginChart& chart, const margrete::rpc::v1::AirCrush& airCrush) const {
    if (airCrush.points_size() < 2) {
        throw std::runtime_error("air crush requires at least two points");
    }
    MP_NOTEINFO rootInfo = BaseInfo(airCrush.base(), MP_NOTETYPE_AIRCRUSH);
    rootInfo.longAttr = MP_NOTELONGATTR_BEGIN;
    rootInfo.variationId = airCrush.variation_id();
    rootInfo.optionValue = airCrush.option_value();
    rootInfo.height = airCrush.points(0).height();
    IMargretePluginNote& root = createNote(chart, rootInfo);
    for (int i = 1; i < airCrush.points_size(); ++i) {
        const auto& point = airCrush.points(i);
        MP_NOTEINFO info = rootInfo;
        info.longAttr = i == airCrush.points_size() - 1 ? MP_NOTELONGATTR_END : ToLongAttr(point.attr());
        info.tick = airCrush.base().tick() + point.dt();
        info.x = point.lane();
        info.width = point.width();
        info.height = point.height();
        IMargretePluginNote& child = createNote(chart, info);
        root.appendChild(&child);
    }
    if (chart.appendNote(&root) != MP_TRUE) {
        throw std::runtime_error("failed to append air crush");
    }
}

void ChartMapper::appendRaw(IMargretePluginChart& chart, const margrete::rpc::v1::RawNoteNode& raw) const {
    IMargretePluginNote& root = createRawTree(chart, raw);
    if (chart.appendNote(&root) != MP_TRUE) {
        throw std::runtime_error("failed to append raw note");
    }
}

IMargretePluginNote& ChartMapper::createRawTree(IMargretePluginChart& chart, const margrete::rpc::v1::RawNoteNode& raw) const {
    // Raw nodes mirror RPC fields into MP_NOTEINFO without re-validating lane geometry.
    MP_NOTEINFO info{};
    info.type = static_cast<MpInteger>(raw.type());
    info.longAttr = static_cast<MpInteger>(raw.long_attr());
    info.direction = static_cast<MpInteger>(raw.direction());
    info.exAttr = static_cast<MpInteger>(raw.ex_attr());
    info.variationId = raw.variation_id();
    info.x = raw.x();
    info.width = raw.width();
    info.height = raw.height();
    info.tick = raw.tick();
    info.timelineId = raw.timeline_id();
    info.optionValue = raw.option_value();
    IMargretePluginNote& note = createNote(chart, info);
    for (const auto& rawChild : raw.children()) {
        IMargretePluginNote& child = createRawTree(chart, rawChild);
        note.appendChild(&child);
    }
    return note;
}

void ChartMapper::appendEvent(IMargretePluginChart&, const margrete::rpc::v1::EventObject&) const {
    throw std::runtime_error("event append requires Margrete event interface implementation");
}
