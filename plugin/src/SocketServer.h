#pragma once

#include <atomic>
#include <cstdint>
#include <thread>

#include "Logger.h"
#include "RequestRouter.h"

class SocketServer
{
  public:
    SocketServer(std::uint16_t port, RequestRouter &router, Logger &logger);
    ~SocketServer();

    void start();
    void stop();
    bool running() const noexcept;

  private:
    void run();
    void handleClient(uintptr_t socketHandle);

    std::uint16_t port_;
    RequestRouter &router_;
    Logger &logger_;
    std::atomic_bool running_{false};
    std::jthread thread_;
    uintptr_t listenSocket_{~uintptr_t{0}};
};
