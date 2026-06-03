#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

struct ServerConfig
{
    std::filesystem::path sourcePath{};
    bool loadedFromFile{false};
    std::string host{"127.0.0.1"};
    std::uint16_t port{0};
    bool autoPort{true};
};

ServerConfig LoadServerConfig(const std::filesystem::path &iniPath);
