#pragma once

#include <MargretePlugin.h>

#include "margrete/rpc/v1/messages.pb.h"

class ChartMapper
{
  public:
    void appendItem(IMargretePluginChart &chart, const margrete::rpc::v1::AppendItem &item) const;

  private:
    IMargretePluginNote &createNote(IMargretePluginChart &chart, const MP_NOTEINFO &info) const;
    void appendRaw(IMargretePluginChart &chart, const margrete::rpc::v1::RawNoteNode &raw) const;
    IMargretePluginNote &createRawTree(IMargretePluginChart &chart, const margrete::rpc::v1::RawNoteNode &raw) const;
    void appendLaneNote(IMargretePluginChart &chart, const margrete::rpc::v1::LaneNote &base, MpInteger type,
                        MpInteger direction) const;
    void appendHold(IMargretePluginChart &chart, const margrete::rpc::v1::Hold &hold) const;
    void appendSlide(IMargretePluginChart &chart, const margrete::rpc::v1::Slide &slide) const;
    void appendAir(IMargretePluginChart &chart, const margrete::rpc::v1::Air &air) const;
    void appendAirHold(IMargretePluginChart &chart, const margrete::rpc::v1::AirHold &airHold) const;
    void appendAirSlide(IMargretePluginChart &chart, const margrete::rpc::v1::AirSlide &airSlide) const;
    void appendAirCrush(IMargretePluginChart &chart, const margrete::rpc::v1::AirCrush &airCrush) const;
    void appendEvent(IMargretePluginChart &chart, const margrete::rpc::v1::EventObject &event) const;
};
