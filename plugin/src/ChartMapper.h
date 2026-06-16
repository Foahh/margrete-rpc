#pragma once

#include <cstdint>
#include <vector>

#include <MargretePlugin.h>

#include "margrete/rpc/v1/messages.pb.h"

class ChartMapper
{
  public:
    static std::vector<margrete::rpc::v1::Note> SnapshotNotes(IMargretePluginChart &chart);
    static void SnapshotForEdit(IMargretePluginChart &chart, MpInteger eventScanExtraTicks,
                                const std::vector<std::int32_t> &eventScanTil, bool noteTilOnly,
                                margrete::rpc::v1::BeginEditResponse &response);
    static margrete::rpc::v1::Note NoteToProto(IMargretePluginNote &note);
    static MP_NOTEINFO ProtoToNoteInfo(const margrete::rpc::v1::Note &note);
};
