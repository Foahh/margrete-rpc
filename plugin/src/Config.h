#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

struct ServerConfig
{
    std::string host{"127.0.0.1"};
    std::uint16_t port{48731};
    std::filesystem::path logPath{"margrete-rpc.log"};
};

ServerConfig LoadServerConfig(const std::filesystem::path &iniPath);
