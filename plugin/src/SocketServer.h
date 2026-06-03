#pragma once

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_set>
#include <vector>

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
    static constexpr uintptr_t InvalidSocketHandle = ~uintptr_t{0};

    struct ClientThread
    {
        std::thread thread;
        std::shared_ptr<std::atomic_bool> done;
    };

    void run();
    void handleClient(uintptr_t socketHandle);
    void registerClient(uintptr_t socketHandle);
    void closeClient(uintptr_t socketHandle);
    void shutdownClients();
    void reapClientThreads(bool joinAll);

    std::string host_;
    std::uint16_t port_;
    RequestRouter &router_;
    Logger &logger_;
    StartedCallback onStarted_;
    std::atomic_bool running_{false};
    std::atomic_uint16_t actualPort_{0};
    std::jthread thread_;
    std::atomic<uintptr_t> listenSocket_{InvalidSocketHandle};
    std::mutex clientMutex_;
    std::unordered_set<uintptr_t> clientSockets_;
    std::vector<ClientThread> clientThreads_;
};
