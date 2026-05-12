#include "ServerController.h"

ServerController::ServerController(ServerConfig config)
    : config_(std::move(config)), logger_(config_.logPath), router_(nullptr, config_)
{
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
    server_->start();
}

void ServerController::stop()
{
    if (server_)
    {
        server_->stop();
        server_.reset();
    }
    router_.setContext(nullptr);
}
