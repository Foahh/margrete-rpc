#include "ServerController.h"

#include <string>

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
    if (!config_.sourcePath.empty())
    {
        logger_.info("config path=" + config_.sourcePath.string() +
                     (config_.loadedFromFile ? " (loaded)" : " (not found; using defaults)"));
    }
    logger_.info("config loaded host=" + config_.host +
                 " port=" + (config_.autoPort ? std::string("auto") : std::to_string(config_.port)) +
                 " resolved_log=" + logPath_.string());
    logger_.info("instance id=" + instanceId_);
}

bool ServerController::running() const noexcept
{
    return server_ && server_->running();
}

void ServerController::toggle(IMargretePluginContext *context)
{
    if (running())
    {
        stop();
        return;
    }
    router_.setContext(context);
    router_.setLogger(&logger_);
    server_ = std::make_unique<SocketServer>(config_.port, router_, logger_, [this](std::uint16_t port) {
        DiscoveryRegistry::Publish(instanceId_, port, logPath_, PRODUCT_VERSION, logger_);
        discoveryPublished_.store(true);
    });
    logger_.info("server starting");
    server_->start();
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
