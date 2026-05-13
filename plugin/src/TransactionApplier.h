#pragma once

#include "MargreteSession.h"
#include "margrete/rpc/v1/messages.pb.h"

class TransactionApplier
{
  public:
    static void ApplyEdit(MargreteSession &session, const margrete::rpc::v1::ApplyEditRequest &request);
};
