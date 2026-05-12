#pragma once

#include <vector>

#include <MargretePlugin.h>

#include "margrete/rpc/v1/messages.pb.h"

class ChartMapper
{
  public:
    static std::vector<margrete::rpc::v1::Note> SnapshotNotes(IMargretePluginChart &chart);
    static void SnapshotForEdit(IMargretePluginChart &chart, MpInteger eventScanExtraTicks, MpInteger maxScanTil,
                                margrete::rpc::v1::BeginEditResponse &response);
    static margrete::rpc::v1::Note NoteToProto(IMargretePluginNote &note);
    static MP_NOTEINFO ProtoToNoteInfo(const margrete::rpc::v1::Note &note);
};
