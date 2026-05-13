#include "ServerController.h"

#include <string>

ServerController::ServerController(ServerConfig config)
    : config_(std::move(config)), logger_(config_.logPath), router_(nullptr, config_)
{
    router_.setLogger(&logger_);
    if (!config_.sourcePath.empty())
    {
        logger_.info("config path=" + config_.sourcePath.string() +
                     (config_.loadedFromFile ? " (loaded)" : " (not found; using defaults)"));
    }
    logger_.info("config loaded host=" + config_.host + " port=" + std::to_string(config_.port) + " log=" +
                 config_.logPath.string() + " event_scan_extra_ticks=" + std::to_string(config_.eventScanExtraTicks) +
                 " event_scan_max_til=" + std::to_string(config_.eventScanMaxTil));
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
    server_ = std::make_unique<SocketServer>(config_.port, router_, logger_);
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
    router_.setContext(nullptr);
    router_.setLogger(nullptr);
}
