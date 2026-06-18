#include "NamedPipeServer.h"

#include <array>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "FrameProtocol.h"

namespace
{
std::wstring Utf8ToWide(const std::string &value)
{
    if (value.empty())
    {
        return {};
    }
    const int size = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), nullptr, 0);
    if (size <= 0)
    {
        throw std::runtime_error("failed to convert pipe name to UTF-16");
    }
    std::wstring out(static_cast<std::size_t>(size), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), out.data(), size);
    return out;
}

std::string LastErrorMessage(const char *prefix)
{
    return std::string(prefix) + " failed error=" + std::to_string(GetLastError());
}
} // namespace

NamedPipeServer::NamedPipeServer(std::string pipeName, RequestRouter &router, Logger &logger,
                                 StartedCallback onStarted)
    : pipeName_(std::move(pipeName)), router_(router), logger_(logger), onStarted_(std::move(onStarted))
{
}

NamedPipeServer::~NamedPipeServer()
{
    stop();
}

void NamedPipeServer::start()
{
    if (running_.exchange(true))
    {
        return;
    }
    thread_ = std::jthread([this] { run(); });
}

void NamedPipeServer::stop()
{
    running_.store(false);
    const HANDLE listenPipe = listenPipe_.exchange(InvalidHandle);
    if (listenPipe != InvalidHandle)
    {
        CloseHandle(listenPipe);
    }
    shutdownClients();
    if (thread_.joinable())
    {
        thread_.request_stop();
        thread_.join();
    }
}

bool NamedPipeServer::running() const noexcept
{
    return running_.load();
}

std::string NamedPipeServer::pipeName() const
{
    return pipeName_;
}

std::string NamedPipeServer::pipePath() const
{
    return "\\\\.\\pipe\\" + pipeName_;
}

void NamedPipeServer::run()
{
    logger_.info("pipe server starting path=" + pipePath());

    const std::wstring path = Utf8ToWide(pipePath());
    bool announced = false;
    while (running_.load())
    {
        reapClientThreads(false);
        HANDLE pipe = CreateNamedPipeW(path.c_str(), PIPE_ACCESS_DUPLEX,
                                       PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                       PIPE_UNLIMITED_INSTANCES, FrameProtocol::MaxFrameSize,
                                       FrameProtocol::MaxFrameSize, 0, nullptr);
        if (pipe == INVALID_HANDLE_VALUE)
        {
            logger_.error(LastErrorMessage("CreateNamedPipeW"));
            break;
        }
        listenPipe_.store(pipe);
        if (!announced && onStarted_)
        {
            onStarted_(pipePath());
            announced = true;
        }

        const BOOL connected = ConnectNamedPipe(pipe, nullptr) ? TRUE : (GetLastError() == ERROR_PIPE_CONNECTED);
        HANDLE expectedListenPipe = pipe;
        const bool stillOwnsListenPipe = listenPipe_.compare_exchange_strong(expectedListenPipe, InvalidHandle);
        if (!stillOwnsListenPipe)
        {
            break;
        }
        if (!connected)
        {
            CloseHandle(pipe);
            if (running_.load())
            {
                logger_.error(LastErrorMessage("ConnectNamedPipe"));
            }
            continue;
        }

        registerClient(pipe);
        auto done = std::make_shared<std::atomic_bool>(false);
        try
        {
            {
                std::scoped_lock lock(clientMutex_);
                clientThreads_.push_back(ClientThread{std::thread{}, done});
            }
            std::thread clientThread([this, pipe, done] {
                handleClient(pipe);
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
            logger_.error(std::string("pipe client thread creation failed: ") + ex.what());
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
            closeClient(pipe);
        }
    }

    running_.store(false);
    const HANDLE listenPipe = listenPipe_.exchange(InvalidHandle);
    if (listenPipe != InvalidHandle)
    {
        CloseHandle(listenPipe);
    }
    shutdownClients();
    reapClientThreads(true);
    logger_.info("pipe server stopped");
}

void NamedPipeServer::handleClient(HANDLE pipe)
{
    auto readExact = [pipe](char *buffer, DWORD size, bool allowCleanEof) {
        DWORD received = 0;
        while (received < size)
        {
            DWORD n = 0;
            if (!ReadFile(pipe, buffer + received, size - received, &n, nullptr))
            {
                if (allowCleanEof && received == 0)
                {
                    return false;
                }
                throw std::runtime_error(LastErrorMessage("ReadFile"));
            }
            if (n == 0)
            {
                if (allowCleanEof && received == 0)
                {
                    return false;
                }
                throw std::runtime_error("pipe client disconnected before frame completed");
            }
            received += n;
        }
        return true;
    };

    auto writeAll = [pipe](const char *buffer, DWORD size) {
        DWORD sent = 0;
        while (sent < size)
        {
            DWORD n = 0;
            if (!WriteFile(pipe, buffer + sent, size - sent, &n, nullptr) || n == 0)
            {
                throw std::runtime_error(LastErrorMessage("WriteFile"));
            }
            sent += n;
        }
    };

    try
    {
        while (running_.load())
        {
            std::array<char, 4> header{};
            if (!readExact(header.data(), 4, true))
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
            readExact(reinterpret_cast<char *>(frame.data() + 4), static_cast<DWORD>(size), false);
            const auto request = FrameProtocol::Decode(frame);
            const auto response = router_.route(request);
            const auto outFrame = FrameProtocol::Encode(response);
            writeAll(reinterpret_cast<const char *>(outFrame.data()), static_cast<DWORD>(outFrame.size()));
        }
    }
    catch (const std::exception &ex)
    {
        logger_.error(std::string(ex.what()));
    }
    closeClient(pipe);
}

void NamedPipeServer::registerClient(HANDLE pipe)
{
    std::scoped_lock lock(clientMutex_);
    clientPipes_.insert(pipe);
}

void NamedPipeServer::closeClient(HANDLE pipe)
{
    std::scoped_lock lock(clientMutex_);
    clientPipes_.erase(pipe);
    DisconnectNamedPipe(pipe);
    CloseHandle(pipe);
}

void NamedPipeServer::shutdownClients()
{
    std::scoped_lock lock(clientMutex_);
    for (const HANDLE pipe : clientPipes_)
    {
        CancelIoEx(pipe, nullptr);
        DisconnectNamedPipe(pipe);
    }
}

void NamedPipeServer::reapClientThreads(bool joinAll)
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
