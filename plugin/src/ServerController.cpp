#include "ServerController.h"

#include <chrono>
#include <string>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

#include "DiscoveryRegistry.h"
#include "Utf8.h"
#include "meta.h"

namespace
{
std::filesystem::path ResolveLogPath(const std::string &instanceId)
{
    const auto path = DiscoveryRegistry::LogPath(instanceId);
    std::error_code ec;
    std::filesystem::create_directories(path.parent_path(), ec);
    return path;
}
} // namespace

ServerController::ServerController(ServerConfig config)
    : config_(std::move(config)), instanceId_(DiscoveryRegistry::CreateInstanceId()),
      logPath_(ResolveLogPath(instanceId_)), logger_(logPath_), router_(nullptr, config_)
{
#ifdef _WIN32
    processId_ = GetCurrentProcessId();
#endif
    router_.setLogger(&logger_);
    router_.setInstanceId(instanceId_);
    router_.setStatusSnapshotProvider([this]() {
        RouterStatusSnapshot snapshot;
        snapshot.pid = processId_;
        snapshot.logPath = PathUtf8(logPath_);
        snapshot.configPath = PathUtf8(config_.sourcePath);
        if (running())
        {
            snapshot.uptime = static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - serverStartTime_)
                    .count());
        }
        return snapshot;
    });
    logConfig(config_, "config initialized");
    logger_.info("instance id=" + instanceId_);
}

bool ServerController::running() const noexcept
{
    return (socketServer_ && socketServer_->running()) || (pipeServer_ && pipeServer_->running());
}

ServerControllerStatus ServerController::status() const
{
    ServerControllerStatus value;
    value.running = running();
    value.discoveryPublished = discoveryPublished_.load();
    value.loadedConfig = config_;
    value.activeConfig = activeConfig_;
    value.hasActiveConfig = hasActiveConfig_;
    value.instanceId = instanceId_;
    value.logPath = logPath_;
    value.actualPort = socketServer_ ? socketServer_->actualPort() : 0;
    {
        std::scoped_lock lock(discoveryMutex_);
        value.actualPipePath = actualPipePath_;
    }
    return value;
}

void ServerController::setConfig(ServerConfig config)
{
    config_ = std::move(config);
    router_.setConfig(config_);
    logConfig(config_, "config reloaded");
}

void ServerController::start(IMargretePluginContext *context)
{
    if (running())
    {
        return;
    }
    activeConfig_ = config_;
    hasActiveConfig_ = true;
    router_.setContext(context);
    router_.setLogger(&logger_);
    router_.setConfig(activeConfig_);

    serverStartTime_ = std::chrono::steady_clock::now();
    logger_.info("server starting");

    if (activeConfig_.transport == ServerTransportMode::Tcp || activeConfig_.transport == ServerTransportMode::Both)
    {
        const std::string publishHost = activeConfig_.host;
        socketServer_ = std::make_unique<SocketServer>(activeConfig_.host, activeConfig_.port, router_, logger_,
                                                       [this, publishHost](std::uint16_t port) {
                                                           {
                                                               std::scoped_lock lock(discoveryMutex_);
                                                               actualPort_ = port;
                                                           }
                                                           publishDiscovery();
                                                       });
        socketServer_->start();
    }

    if (activeConfig_.transport == ServerTransportMode::Pipe || activeConfig_.transport == ServerTransportMode::Both)
    {
        pipeServer_ =
            std::make_unique<NamedPipeServer>(resolvePipeName(), router_, logger_, [this](const std::string &pipePath) {
                {
                    std::scoped_lock lock(discoveryMutex_);
                    actualPipePath_ = pipePath;
                }
                publishDiscovery();
            });
        pipeServer_->start();
    }
}

void ServerController::toggle(IMargretePluginContext *context)
{
    if (running())
    {
        stop();
        return;
    }
    start(context);
}

void ServerController::stop()
{
    if (socketServer_)
    {
        logger_.info("tcp server stopping");
        socketServer_->stop();
        socketServer_.reset();
    }
    if (pipeServer_)
    {
        logger_.info("pipe server stopping");
        pipeServer_->stop();
        pipeServer_.reset();
    }
    if (discoveryPublished_.exchange(false))
    {
        DiscoveryRegistry::Remove(instanceId_, logger_);
    }
    router_.setContext(nullptr);
    router_.setLogger(nullptr);
    {
        std::scoped_lock lock(discoveryMutex_);
        actualPort_ = 0;
        actualPipePath_.clear();
    }
}

void ServerController::logConfig(const ServerConfig &config, const char *label)
{
    if (!config.sourcePath.empty())
    {
        logger_.info(std::string(label) + " path=" + PathUtf8(config.sourcePath) +
                     (config.loadedFromFile ? " (loaded)" : " (not found; using defaults)"));
    }
    logger_.info(std::string(label) + " transport=" + std::string(TransportModeName(config.transport)) + " host=" +
                 config.host + " port=" + (config.autoPort ? std::string("auto") : std::to_string(config.port)) +
                 " pipe_name=" + config.pipeName + " resolved_log=" + PathUtf8(logPath_));
}

void ServerController::publishDiscovery()
{
    std::vector<DiscoveryTransport> transports;
    {
        std::scoped_lock lock(discoveryMutex_);
        if (actualPort_ != 0)
        {
            transports.push_back(DiscoveryTransport{"tcp", activeConfig_.host + ":" + std::to_string(actualPort_), ""});
        }
        if (!actualPipePath_.empty())
        {
            transports.push_back(DiscoveryTransport{"npipe", "", actualPipePath_});
        }
    }
    if (transports.empty())
    {
        return;
    }
    DiscoveryRegistry::Publish(instanceId_, transports, logPath_, PRODUCT_VERSION, logger_);
    discoveryPublished_.store(true);
}

std::string ServerController::resolvePipeName() const
{
    if (activeConfig_.pipeName != "auto")
    {
        return activeConfig_.pipeName;
    }
    return "margrete-rpc-" + instanceId_;
}
