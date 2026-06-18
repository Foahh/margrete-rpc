#pragma once

#include <atomic>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_set>
#include <vector>

#include <windows.h>

#include "Logger.h"
#include "RequestRouter.h"

class NamedPipeServer
{
  public:
    using StartedCallback = std::function<void(const std::string &)>;

    NamedPipeServer(std::string pipeName, RequestRouter &router, Logger &logger, StartedCallback onStarted = {});
    ~NamedPipeServer();

    void start();
    void stop();
    bool running() const noexcept;
    std::string pipeName() const;
    std::string pipePath() const;

  private:
    static constexpr HANDLE InvalidHandle = INVALID_HANDLE_VALUE;

    struct ClientThread
    {
        std::thread thread;
        std::shared_ptr<std::atomic_bool> done;
    };

    void run();
    void handleClient(HANDLE pipe);
    void registerClient(HANDLE pipe);
    void closeClient(HANDLE pipe);
    void shutdownClients();
    void reapClientThreads(bool joinAll);

    std::string pipeName_;
    RequestRouter &router_;
    Logger &logger_;
    StartedCallback onStarted_;
    std::atomic_bool running_{false};
    std::jthread thread_;
    std::atomic<HANDLE> listenPipe_{InvalidHandle};
    std::mutex clientMutex_;
    std::unordered_set<HANDLE> clientPipes_;
    std::vector<ClientThread> clientThreads_;
};
