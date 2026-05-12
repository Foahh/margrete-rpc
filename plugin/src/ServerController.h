#pragma once

#include <memory>

#include <MargretePlugin.h>

#include "Config.h"
#include "Logger.h"
#include "RequestRouter.h"
#include "SocketServer.h"

class ServerController {
public:
    explicit ServerController(ServerConfig config);
    bool running() const noexcept;
    void toggle(IMargretePluginContext* context);
    void stop();

private:
    ServerConfig config_;
    Logger logger_;
    RequestRouter router_;
    std::unique_ptr<SocketServer> server_;
};
