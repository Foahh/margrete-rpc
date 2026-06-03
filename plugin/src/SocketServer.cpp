#include "SocketServer.h"

#include <array>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <winsock2.h>
#include <ws2tcpip.h>

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
    if (listenSocket_ != ~uintptr_t{0})
    {
        closesocket(static_cast<SOCKET>(listenSocket_));
        listenSocket_ = ~uintptr_t{0};
    }
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
    listenSocket_ = static_cast<uintptr_t>(srv);

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port_);
    if (inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1)
    {
        running_.store(false);
        logger_.error("invalid bind host=" + host_);
        closesocket(srv);
        listenSocket_ = ~uintptr_t{0};
        WSACleanup();
        return;
    }

    if (bind(srv, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) == SOCKET_ERROR)
    {
        running_.store(false);
        logger_.error("bind failed");
        closesocket(srv);
        listenSocket_ = ~uintptr_t{0};
        WSACleanup();
        return;
    }

    if (listen(srv, SOMAXCONN) == SOCKET_ERROR)
    {
        running_.store(false);
        logger_.error("listen failed");
        closesocket(srv);
        listenSocket_ = ~uintptr_t{0};
        WSACleanup();
        return;
    }

    sockaddr_in boundAddr{};
    int boundAddrLen = sizeof(boundAddr);
    if (getsockname(srv, reinterpret_cast<sockaddr *>(&boundAddr), &boundAddrLen) == SOCKET_ERROR)
    {
        running_.store(false);
        logger_.error("getsockname failed");
        closesocket(srv);
        listenSocket_ = ~uintptr_t{0};
        WSACleanup();
        return;
    }
    actualPort_.store(ntohs(boundAddr.sin_port));

    logger_.info("server started on " + host_ + ":" + std::to_string(actualPort_.load()));
    if (onStarted_)
    {
        onStarted_(actualPort_.load());
    }
    while (running_.load())
    {
        SOCKET client = accept(srv, nullptr, nullptr);
        if (client == INVALID_SOCKET)
        {
            if (running_.load())
            {
                logger_.error("accept failed");
            }
            break;
        }
        std::thread([this, client] { handleClient(static_cast<uintptr_t>(client)); }).detach();
    }

    running_.store(false);
    actualPort_.store(0);
    if (listenSocket_ == static_cast<uintptr_t>(srv))
    {
        closesocket(srv);
        listenSocket_ = ~uintptr_t{0};
    }
    WSACleanup();
    logger_.info("server stopped");
}

void SocketServer::handleClient(uintptr_t socketHandle)
{
    SOCKET client = static_cast<SOCKET>(socketHandle);
    auto recvExact = [client](char *buffer, int size) {
        int received = 0;
        while (received < size)
        {
            const int n = recv(client, buffer + received, size - received, 0);
            if (n <= 0)
            {
                throw std::runtime_error("client disconnected");
            }
            received += n;
        }
    };

    try
    {
        std::array<char, 4> header{};
        recvExact(header.data(), 4);
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
        recvExact(reinterpret_cast<char *>(frame.data() + 4), static_cast<int>(size));
        const auto request = FrameProtocol::Decode(frame);
        const auto response = router_.route(request);
        const auto outFrame = FrameProtocol::Encode(response);
        send(client, reinterpret_cast<const char *>(outFrame.data()), static_cast<int>(outFrame.size()), 0);
    }
    catch (const std::exception &ex)
    {
        logger_.error(std::string(ex.what()));
    }
    closesocket(client);
}
