#include "ServerController.h"

#include <string>
#include <utility>

#include "DiscoveryRegistry.h"
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
    router_.setLogger(&logger_);
    logConfig(config_, "config initialized");
    logger_.info("instance id=" + instanceId_);
}

bool ServerController::running() const noexcept
{
    return server_ && server_->running();
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
    value.actualPort = server_ ? server_->actualPort() : 0;
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

    const std::string publishHost = activeConfig_.host;
    server_ = std::make_unique<SocketServer>(
        activeConfig_.host, activeConfig_.port, router_, logger_, [this, publishHost](std::uint16_t port) {
            DiscoveryRegistry::Publish(instanceId_, publishHost, port, logPath_, PRODUCT_VERSION, logger_);
            discoveryPublished_.store(true);
        });
    logger_.info("server starting");
    server_->start();
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
    if (server_)
    {
        logger_.info("server stopping");
        server_->stop();
        server_.reset();
    }
    if (discoveryPublished_.exchange(false))
    {
        DiscoveryRegistry::Remove(instanceId_, logger_);
    }
    router_.setContext(nullptr);
    router_.setLogger(nullptr);
}

void ServerController::logConfig(const ServerConfig &config, const char *label)
{
    if (!config.sourcePath.empty())
    {
        logger_.info(std::string(label) + " path=" + config.sourcePath.string() +
                     (config.loadedFromFile ? " (loaded)" : " (not found; using defaults)"));
    }
    logger_.info(std::string(label) + " host=" + config.host +
                 " port=" + (config.autoPort ? std::string("auto") : std::to_string(config.port)) +
                 " resolved_log=" + logPath_.string());
}
