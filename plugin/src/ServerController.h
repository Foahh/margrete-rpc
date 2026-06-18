#pragma once

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <mutex>
#include <string>

#include <MargretePlugin.h>

#include "Config.h"
#include "Logger.h"
#include "NamedPipeServer.h"
#include "RequestRouter.h"
#include "SocketServer.h"

struct ServerControllerStatus
{
    bool running{false};
    bool discoveryPublished{false};
    ServerConfig loadedConfig{};
    ServerConfig activeConfig{};
    bool hasActiveConfig{false};
    std::string instanceId{};
    std::filesystem::path logPath{};
    std::uint16_t actualPort{0};
    std::string actualPipePath{};
};

class ServerController
{
  public:
    explicit ServerController(ServerConfig config);
    bool running() const noexcept;
    ServerControllerStatus status() const;
    void setConfig(ServerConfig config);
    void start(IMargretePluginContext *context);
    void toggle(IMargretePluginContext *context);
    void stop();

  private:
    void logConfig(const ServerConfig &config, const char *label);
    void publishDiscovery();
    std::string resolvePipeName() const;

    ServerConfig config_;
    ServerConfig activeConfig_;
    bool hasActiveConfig_{false};
    std::string instanceId_;
    std::filesystem::path logPath_;
    std::uint32_t processId_{0};
    std::chrono::steady_clock::time_point serverStartTime_{};
    Logger logger_;
    RequestRouter router_;
    std::unique_ptr<SocketServer> socketServer_;
    std::unique_ptr<NamedPipeServer> pipeServer_;
    std::atomic_bool discoveryPublished_{false};
    mutable std::mutex discoveryMutex_;
    std::uint16_t actualPort_{0};
    std::string actualPipePath_;
};
