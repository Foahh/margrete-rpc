#pragma once

#include <MargretePlugin.h>

#include "TransactionApplier.h"
#include "margrete/rpc/v1/messages.pb.h"

class RequestRouter
{
  public:
    explicit RequestRouter(IMargretePluginContext *context);
    margrete::rpc::v1::Envelope route(const margrete::rpc::v1::Envelope &request);
    void setContext(IMargretePluginContext *context);

  private:
    margrete::rpc::v1::Envelope error(std::uint64_t requestId, margrete::rpc::v1::ErrorCode code,
                                      const std::string &message) const;

    IMargretePluginContext *context_{nullptr};
    TransactionApplier applier_;
};
