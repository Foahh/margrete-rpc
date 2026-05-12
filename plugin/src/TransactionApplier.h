#pragma once

#include "MargreteSession.h"
#include "margrete/rpc/v1/messages.pb.h"

class TransactionApplier
{
  public:
    static void ApplyAppend(MargreteSession &session, const margrete::rpc::v1::ApplyAppendPatchRequest &request);
    static void ApplyEdit(MargreteSession &session, const margrete::rpc::v1::ApplyEditPatchRequest &request);
};
