#pragma once

#include <cstdint>
#include <functional>
#include <mutex>
#include <string>

#include <MargretePlugin.h>

#include "Config.h"
#include "Logger.h"
#include "margrete/rpc/v1/messages.pb.h"

struct RouterStatusSnapshot
{
    std::uint64_t uptime{0};
    std::uint32_t pid{0};
    std::string logPath;
    std::string configPath;
};

using StatusSnapshotProvider = std::function<RouterStatusSnapshot()>;

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
    void setConfig(ServerConfig config);
    void setInstanceId(std::string instanceId);
    void setStatusSnapshotProvider(StatusSnapshotProvider provider);
    void setLogger(Logger *logger);

  private:
    margrete::rpc::v1::Envelope error(std::uint64_t requestId, margrete::rpc::v1::ErrorCode code,
                                      const std::string &message) const;
    MargreteComPtr<IMargretePluginContext> retainContext() const;
    void logInfo(const std::string &message) const;
    void logError(const std::string &message) const;
    static const char *requestKind(const margrete::rpc::v1::Envelope &request) noexcept;

    mutable std::mutex contextMutex_;
    IMargretePluginContext *context_{nullptr};
    Logger *logger_{nullptr};
    ServerConfig config_;
    std::string instanceId_;
    StatusSnapshotProvider statusSnapshotProvider_;
};
