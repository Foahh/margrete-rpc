#pragma once

#include <atomic>
#include <cstdint>
#include <functional>
#include <string>
#include <thread>

#include "Logger.h"
#include "RequestRouter.h"

class SocketServer
{
  public:
    using StartedCallback = std::function<void(std::uint16_t)>;

    SocketServer(std::string host, std::uint16_t port, RequestRouter &router, Logger &logger,
                 StartedCallback onStarted = {});
    ~SocketServer();

    void start();
    void stop();
    bool running() const noexcept;
    std::uint16_t actualPort() const noexcept;

  private:
    void run();
    void handleClient(uintptr_t socketHandle);

    std::string host_;
    std::uint16_t port_;
    RequestRouter &router_;
    Logger &logger_;
    StartedCallback onStarted_;
    std::atomic_bool running_{false};
    std::atomic_uint16_t actualPort_{0};
    std::jthread thread_;
    uintptr_t listenSocket_{~uintptr_t{0}};
};
