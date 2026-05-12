#pragma once

#include <mutex>

#include <MargretePlugin.h>

#include "Config.h"
#include "margrete/rpc/v1/messages.pb.h"

class RequestRouter
{
  public:
    explicit RequestRouter(IMargretePluginContext *context);
    RequestRouter(IMargretePluginContext *context, ServerConfig config);
    ~RequestRouter();
    RequestRouter(const RequestRouter &) = delete;
    RequestRouter &operator=(const RequestRouter &) = delete;

    margrete::rpc::v1::Envelope route(const margrete::rpc::v1::Envelope &request);
    void setContext(IMargretePluginContext *context);

  private:
    margrete::rpc::v1::Envelope error(std::uint64_t requestId, margrete::rpc::v1::ErrorCode code,
                                      const std::string &message) const;
    MargreteComPtr<IMargretePluginContext> retainContext() const;

    mutable std::mutex contextMutex_;
    IMargretePluginContext *context_{nullptr};
    ServerConfig config_;
};
