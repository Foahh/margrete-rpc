#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>

enum class ServerTransportMode
{
    Tcp,
    Pipe,
    Both,
};

struct ServerConfig
{
    std::filesystem::path sourcePath{};
    bool loadedFromFile{false};
    ServerTransportMode transport{ServerTransportMode::Both};
    std::string host{"127.0.0.1"};
    std::uint16_t port{0};
    bool autoPort{true};
    std::string pipeName{"auto"};
};

ServerConfig LoadServerConfig(const std::filesystem::path &iniPath);

bool IsLoopbackAddress(std::string_view host);
std::string_view TransportModeName(ServerTransportMode mode);
