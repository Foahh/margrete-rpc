#include "SocketServer.h"

#include <array>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <winsock2.h>
#include <ws2tcpip.h>

#include "Config.h"
#include "FrameProtocol.h"

SocketServer::SocketServer(std::string host, std::uint16_t port, RequestRouter &router, Logger &logger,
                           StartedCallback onStarted)
    : host_(std::move(host)), port_(port), router_(router), logger_(logger), onStarted_(std::move(onStarted))
{
}

SocketServer::~SocketServer()
{
    stop();
}

void SocketServer::start()
{
    if (running_.exchange(true))
    {
        return;
    }
    thread_ = std::jthread([this] { run(); });
}

void SocketServer::stop()
{
    running_.store(false);
    const uintptr_t listenSocket = listenSocket_.exchange(InvalidSocketHandle);
    if (listenSocket != InvalidSocketHandle)
    {
        closesocket(static_cast<SOCKET>(listenSocket));
    }
    shutdownClients();
    if (thread_.joinable())
    {
        thread_.request_stop();
        thread_.join();
    }
}

bool SocketServer::running() const noexcept
{
    return running_.load();
}

std::uint16_t SocketServer::actualPort() const noexcept
{
    return actualPort_.load();
}

void SocketServer::run()
{
    WSADATA wsa{};
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0)
    {
        running_.store(false);
        logger_.error("WSAStartup failed");
        return;
    }

    SOCKET srv = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (srv == INVALID_SOCKET)
    {
        running_.store(false);
        logger_.error("socket creation failed");
        WSACleanup();
        return;
    }
    listenSocket_.store(static_cast<uintptr_t>(srv));
    const auto closeListenSocket = [&]() {
        const uintptr_t previousListenSocket = listenSocket_.exchange(InvalidSocketHandle);
        if (previousListenSocket == static_cast<uintptr_t>(srv))
        {
            closesocket(srv);
        }
    };

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    if (inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1)
    {
        running_.store(false);
        logger_.error("invalid bind host=" + host_);
        closeListenSocket();
        WSACleanup();
        return;
    }

    if (bind(srv, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) == SOCKET_ERROR)
    {
        running_.store(false);
        logger_.error("bind failed");
        closeListenSocket();
        WSACleanup();
        return;
    }

    if (listen(srv, SOMAXCONN) == SOCKET_ERROR)
    {
        running_.store(false);
        logger_.error("listen failed");
        closeListenSocket();
        WSACleanup();
        return;
    }

    sockaddr_in boundAddr{};
    int boundAddrLen = sizeof(boundAddr);
    if (getsockname(srv, reinterpret_cast<sockaddr *>(&boundAddr), &boundAddrLen) == SOCKET_ERROR)
    {
        running_.store(false);
        logger_.error("getsockname failed");
        closeListenSocket();
        WSACleanup();
        return;
    }
    actualPort_.store(ntohs(boundAddr.sin_port));

    logger_.info("server started on " + host_ + ":" + std::to_string(actualPort_.load()));
    if (!IsLoopbackAddress(host_))
    {
        logger_.info("WARNING: server bound to non-loopback host " + host_ +
                     "; other machines on this network can connect. "
                     "Set host=127.0.0.1 in margrete-rpc.ini to restrict access to this machine.");
    }
    if (onStarted_)
    {
        onStarted_(actualPort_.load());
    }
    while (running_.load())
    {
        reapClientThreads(false);
        fd_set readSet{};
        FD_ZERO(&readSet);
        FD_SET(srv, &readSet);
        timeval timeout{};
        timeout.tv_sec = 0;
        timeout.tv_usec = 250000;
        const int ready = select(0, &readSet, nullptr, nullptr, &timeout);
        if (ready == SOCKET_ERROR)
        {
            if (running_.load())
            {
                logger_.error("select failed");
            }
            break;
        }
        if (ready == 0)
        {
            continue;
        }

        SOCKET client = accept(srv, nullptr, nullptr);
        if (client == INVALID_SOCKET)
        {
            if (running_.load())
            {
                logger_.error("accept failed");
            }
            break;
        }
        const auto socketHandle = static_cast<uintptr_t>(client);
        registerClient(socketHandle);
        auto done = std::make_shared<std::atomic_bool>(false);
        try
        {
            {
                std::scoped_lock lock(clientMutex_);
                clientThreads_.push_back(ClientThread{std::thread{}, done});
            }
            std::thread clientThread([this, socketHandle, done] {
                handleClient(socketHandle);
                done->store(true);
            });
            {
                std::scoped_lock lock(clientMutex_);
                for (auto &entry : clientThreads_)
                {
                    if (entry.done == done)
                    {
                        entry.thread = std::move(clientThread);
                        break;
                    }
                }
            }
        }
        catch (const std::exception &ex)
        {
            logger_.error(std::string("client thread creation failed: ") + ex.what());
            {
                std::scoped_lock lock(clientMutex_);
                auto it = clientThreads_.begin();
                while (it != clientThreads_.end())
                {
                    if (it->done == done)
                    {
                        it = clientThreads_.erase(it);
                    }
                    else
                    {
                        ++it;
                    }
                }
            }
            closeClient(socketHandle);
        }
    }

    running_.store(false);
    actualPort_.store(0);
    closeListenSocket();
    shutdownClients();
    reapClientThreads(true);
    WSACleanup();
    logger_.info("server stopped");
}

void SocketServer::handleClient(uintptr_t socketHandle)
{
    SOCKET client = static_cast<SOCKET>(socketHandle);
    auto recvExact = [client](char *buffer, int size, bool allowCleanEof) {
        int received = 0;
        while (received < size)
        {
            const int n = recv(client, buffer + received, size - received, 0);
            if (n == 0)
            {
                if (allowCleanEof && received == 0)
                {
                    return false;
                }
                throw std::runtime_error("client disconnected before frame completed");
            }
            if (n < 0)
            {
                throw std::runtime_error("client disconnected");
            }
            received += n;
        }
        return true;
    };

    auto sendAll = [client](const char *buffer, int size) {
        int sent = 0;
        while (sent < size)
        {
            const int n = send(client, buffer + sent, size - sent, 0);
            if (n == SOCKET_ERROR || n <= 0)
            {
                throw std::runtime_error("failed to send response frame");
            }
            sent += n;
        }
    };

    try
    {
        while (running_.load())
        {
            std::array<char, 4> header{};
            if (!recvExact(header.data(), 4, true))
            {
                break;
            }
            const auto size = static_cast<std::uint32_t>(static_cast<unsigned char>(header[0])) |
                              (static_cast<std::uint32_t>(static_cast<unsigned char>(header[1])) << 8) |
                              (static_cast<std::uint32_t>(static_cast<unsigned char>(header[2])) << 16) |
                              (static_cast<std::uint32_t>(static_cast<unsigned char>(header[3])) << 24);
            if (size > FrameProtocol::MaxFrameSize)
            {
                throw std::runtime_error("frame payload is too large");
            }
            std::vector<std::byte> frame(4 + size);
            for (int i = 0; i < 4; ++i)
            {
                frame[static_cast<std::size_t>(i)] = static_cast<std::byte>(header[static_cast<std::size_t>(i)]);
            }
            recvExact(reinterpret_cast<char *>(frame.data() + 4), static_cast<int>(size), false);
            const auto request = FrameProtocol::Decode(frame);
            const auto response = router_.route(request);
            const auto outFrame = FrameProtocol::Encode(response);
            sendAll(reinterpret_cast<const char *>(outFrame.data()), static_cast<int>(outFrame.size()));
        }
    }
    catch (const std::exception &ex)
    {
        logger_.error(std::string(ex.what()));
    }
    closeClient(socketHandle);
}

void SocketServer::registerClient(uintptr_t socketHandle)
{
    std::scoped_lock lock(clientMutex_);
    clientSockets_.insert(socketHandle);
}

void SocketServer::closeClient(uintptr_t socketHandle)
{
    std::scoped_lock lock(clientMutex_);
    clientSockets_.erase(socketHandle);
    closesocket(static_cast<SOCKET>(socketHandle));
}

void SocketServer::shutdownClients()
{
    std::scoped_lock lock(clientMutex_);
    for (const uintptr_t socketHandle : clientSockets_)
    {
        shutdown(static_cast<SOCKET>(socketHandle), SD_BOTH);
    }
}

void SocketServer::reapClientThreads(bool joinAll)
{
    std::vector<std::thread> threadsToJoin;
    {
        std::scoped_lock lock(clientMutex_);
        auto it = clientThreads_.begin();
        while (it != clientThreads_.end())
        {
            if (joinAll || it->done->load())
            {
                threadsToJoin.push_back(std::move(it->thread));
                it = clientThreads_.erase(it);
            }
            else
            {
                ++it;
            }
        }
    }

    for (auto &thread : threadsToJoin)
    {
        if (thread.joinable())
        {
            thread.join();
        }
    }
}
